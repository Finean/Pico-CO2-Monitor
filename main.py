import breakout_scd41
import font_lib as font
import framebuf
import gc
import _thread
import uasyncio as asyncio
import utils

from pimoroni_i2c import PimoroniI2C
from pimoroni import BREAKOUT_GARDEN_I2C_PINS, RGBLED 
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY_2, PEN_RGB565
from machine import Pin, RTC

#Telem
import time

#Allow USB to initialise
time.sleep(0.5)

lcd = PicoGraphics(display = DISPLAY_PICO_DISPLAY_2, pen_type = PEN_RGB565) #320 x 240 pixels
display_width, display_height = lcd.get_bounds()
lcd.set_backlight(1.0)

#GPIO vars
button_a = Pin(12, Pin.IN, Pin.PULL_UP)
button_b = Pin(13, Pin.IN, Pin.PULL_UP)
button_x = Pin(14, Pin.IN, Pin.PULL_UP)
button_y = Pin(15, Pin.IN, Pin.PULL_UP)
led = RGBLED(26, 27, 28)
led.set_rgb(0, 0, 0)

#Init scd41
i2c = PimoroniI2C(**BREAKOUT_GARDEN_I2C_PINS)
breakout_scd41.init(i2c)
breakout_scd41.start()
last_reading = 0


#Render vars
push_ready = True
render_ready = True
state = "ready"
lock = _thread.allocate_lock()
temp_setting = "Err"
main_state = 0

#Create buffer
disp_buffer = framebuf.FrameBuffer(bytearray(display_width * display_height * 2), display_width, display_height, framebuf.RGB565)
disp_buffer.fill(0)
lcd.set_framebuffer(disp_buffer)
lcd.update()
draw_buffer = framebuf.FrameBuffer(bytearray(display_width * display_height * 2), display_width, display_height, framebuf.RGB565)


def colour(col):
    return (col >> 5) + (col << 11)

WHITE = 0xffff
BLACK = 0x0000
RED = colour(0xf800)
GREEN = colour(0x07e0)
BLUE = colour(0x001f)
YELLOW = colour(0xffc0)

c_lib = {"WHITE": WHITE, "BLACK": BLACK, "RED": RED, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW}


def clear(col = 0x0000):
    asyncio.run(render(draw_fill, (col), mode = "static"))
    led.set_rgb(0, 0, 0)


async def draw_fill(buffer, colour):
    buffer.fill(colour)
    
    
async def read_sensor():
    while True:
        if breakout_scd41.ready():
            return breakout_scd41.measure()
        await asyncio.sleep(0.1)   


def init():
    global last_reading
    dump_reads = []
    read_out = [1, 0, 0]
    i2c = PimoroniI2C(**BREAKOUT_GARDEN_I2C_PINS)  # or PICO_EXPLORER_I2C_PINS or HEADER_I2C_PINS
    asyncio.run(render(init_screen, ([1, 0, 0], []), mode = "static"))
    network = utils.network_connect(utils.NET_SSID, utils.NET_PSK)
    time.sleep(0.25)
    if network:
        read_out[0] = 3
        read_out[1] = 1
        asyncio.run(render(init_screen, (read_out, []), mode = "static"))
        if utils.config["ntc_upd"]:
            time_sync = utils.sync_time()
            if time_sync:
                read_out[1] = 3    
            else:
                read_out[1] = 2
        else:
            read_out[1] = 2
    else:
        read_out[0] = 2
        read_out[1] = 2
    read_out[2] = 1
    asyncio.run(render(init_screen, (read_out, []), mode = "static"))
    time.sleep(0.25)
    read_out[2] = 3
    asyncio.run(render(init_screen, (read_out, []), mode = "static"))
    
    while len(dump_reads) < 3:
        init_read, _, _ = asyncio.run(read_sensor())
        dump_reads.append(init_read)
        asyncio.run(render(init_screen, (read_out, dump_reads), mode = "static"))
    last_reading = init_read
    time.sleep(1.0)
    clear()
    return(True)
    
      
async def init_screen(buffer, args = ([0, 0, 0], [])):
    # Wait Test Fail Pass - white, blue, red, green
    #[ Test ] Wifi
    #[ Wait ] RTC Sync
    #[ Wait ] SCD41 Sensor on I2C 0x62
    #Sensor Init...
    #SCD41 I2C: XXXXppm
    #SCD41 I2C: XXXXppm
    #SCD41 I2C: XXXXppm
    #Booting...
    attr = args[0]
    sensor_reads = args[1]
    buffer.fill(0)
    init_s_reads = 3
    font.text(buffer, "[      ] Wifi", 5, 5, 1, 0xffff)
    font.text(buffer, "[      ] RTC Sync", 5, 13, 1, 0xffff)
    font.text(buffer, "[      ] SCD41 Sensor on I2C 0x62", 5, 21, 1, 0xffff)
    init_colours = [0xffff, BLUE, RED, GREEN]
    init_text = ["WAIT", "TEST", "FAIL", "PASS"]
    for i in range(3):
        font.text(buffer, init_text[attr[i]], 18, 5 + 8 * i, 1, init_colours[attr[i]])
    if attr[2] == 3:
        font.text(buffer, "Sensor initialising...", 5, 29, 1, 0xffff)
    elif attr[2] == 2:
        font.text(buffer, "No sensor detected", 5, 29, 1, 0xffff)
    for j in range(min(init_s_reads, len(sensor_reads))):
        font.text(buffer, f"SCD41 I2C Read: {sensor_reads[j]}", 5, 37 + 8 * j, 1, 0xffff)
    if len(sensor_reads) >= init_s_reads:
        font.text(buffer, "Booting...", 5, 37 + 8 * init_s_reads, 1, 0xffff)
    

async def draw_test(buffer, t, fps = 0):
    buffer.fill(0)
    buffer.rect(0 ,0 ,107, display_height, RED, True)
    buffer.rect(107, 0, 106, display_height, GREEN, True)
    buffer.rect(213, 0, 107, display_height, BLUE, True)
    buffer.rect(0, 120, display_width, 40, 0xffff, True)
    buffer.rect(0, 160, display_width, 40, 0x0000, True)
    buffer.rect(0, 200, display_width, 40, colour(0x528a), True)
    font.textbox(buffer, "Frame Buffer Test Multiline textbox", 5, 5, 200, 0x0000, None, text_size = 2, align = "left", offset = [0,0], draw = True)
    font.text(buffer, "Custom Font", 5, 45, 4, 0x0000)
    font.text(buffer, f"Frame:{t}", 5, 45 + 4 * 8 + 10, 4, 0x0000)
    font.text(buffer, f"{fps:.1f}fps", 5, 45 + 8 * 8 + 20, 4, 0x0000)
    font.wordbox(buffer, "Text centered on multiple lines", 5, 45 + 12 * 8 + 30, 310, 0xffff, None, text_size = 3, align = "center")
    
    
def fahrenheit(celsius):
    x = int(celsius) * (9/5) + 32
    if x > 100:
        return int(round(x, 0))
    else:
        return round(x, 1)


def draw_graph(buffer, data, x, y, w, h, draw_line = True):
    global WIDTH
    global HEIGHT
    data_range = [400, 5000]
    graph = utils.config["graph"]
    graph_max_time = utils.config["graph_max_time"]
    graph_axes = utils.config["graph_axes"]
    graph_show_pts = utils.config["graph_show_pts"]
    graph_padding = utils.config["graph_padding"]
    draw_colour = 0xffff
    line_colour = c_lib[utils.config["line_colour"]]
    font_colour = c_lib[utils.config["font_colour"]]
    axis_colour = c_lib[utils.config["axis_colour"]]
    max_colour = c_lib[utils.config["max_colour"]]
    min_colour = c_lib[utils.config["min_colour"]]
    
    #Do not draw outside of buffer
    x = min(x, 320)
    y = min(y, 240)
    w = min(w, 320 - x)
    h = min(h, 240 - y)
    
    if w < 80 or h < 20:
        print("Insufficient space for graph")
        return

    #If graph = False, draw empty graph
    if not(graph):
        buffer.rect(x, y, w, h, font_colour, False)
        font.text(buffer, "Graph drawing disabled", x + 10, y + 10, 1, font_colour)
        font.text(buffer, "Use settings to enable", x + 10, y + 20, 1, font_colour)
        return
    
    #Draw axes, do not plot
    if len(data) < 2:
        buffer.rect(x, y, w, h, draw_colour, False)
        font.text(buffer, "Graph waiting for data...", x + 10, y + 10, 1, font_colour)
        return

    #Trim data to required time scale
    idx_offset = 0
    cur_time = time.time()
    for ix, val in enumerate(data):
        if (cur_time - val[1]) // 60 > graph_max_time:
            idx_offset = ix + 1
        else:
            break     
    data = data[idx_offset:]
    
    max_val = (400, 0)
    min_val = (5000, 0)
    #Find min/max values
    for ix, val in enumerate(data):
        if val[0] <= min_val[0]:
            min_val = (val[0], ix)
        if val[0] >= max_val[0]:
            max_val = (val[0], ix)
       
    delta_time = max(data[-1][1] - data[0][1], 1) #Seconds
    plot_bounds = (max(350, min_val[0] - graph_padding), min(5500, max_val[0] + graph_padding))
            
    #Draw axes and labels
    if graph_axes:
        bounds = (x + 24, y, x + w, y + h - 10)
        font.text(buffer, f"{plot_bounds[1]}", x, y, 1, font_colour)
        font.text(buffer, f"{plot_bounds[0]}", x, y + h - 16, 1, font_colour)
        font.text(buffer, f"{(plot_bounds[0] + plot_bounds[1]) // 2}", x, y + h // 2 - 12, 1, font_colour)
        font.text(buffer, f"{delta_time // 60} mins ago", x + 24, y + h - 8, 1, font_colour)
        font.text(buffer, "now", x + w - 24, y + h - 8, 1, font_colour)
    else:
        bounds = (x, y, x + w, y + h)
        
    buffer.line(bounds[0], bounds[1], bounds[0], bounds[3], axis_colour)
    buffer.line(bounds[0], bounds[3], bounds[2], bounds[3], axis_colour)
    
    
    if not(draw_line):
        return
    
    prev = None #Last point
    #data_point = (co2 ppm, time.time())
    for ix, data_point in enumerate(data):
        x_val = int(bounds[0] + ((data_point[1] - data[0][1]) / (delta_time)) * (bounds[2] - bounds[0]))
        try:
            y_val = int(bounds[3] - ((data_point[0] - plot_bounds[0]) / (plot_bounds[1] - plot_bounds[0])) * (bounds[3] - bounds[1]))
        except:
            y_val = int(bounds[3] + (bounds[3] - bounds[1]) // 2)
        
        #Draw line
        if not(prev is None):
            buffer.line(prev[0], prev[1], x_val, y_val, line_colour)
        
        if graph_show_pts:
            if ix == max_val[1]:
                font.text(buffer, f"{data_point[0]}", min(bounds[2] - 24, max(bounds[0] + 4, x_val - 10)), max(y_val - 12, bounds[1]), 1, max_colour)
            elif ix == min_val[1]:
                font.text(buffer, f"{data_point[0]}", min(bounds[2] - 24, max(bounds[0] + 4, x_val - 10)), min(bounds[3] - 8, y_val + 4), 1, min_colour)
        
        prev = (x_val, y_val)


async def program_draw(buffer, get_values):
    #args = ([co2, temp, humidity], [graph_data], menu_state)
    global temp_setting
    args = get_values()
    readings = args[0]
    c_time = parse_time()
    graph_data = args[1]
    state = args[2]
    bg_colour = c_lib[utils.config["bg_colour"]]
    font_colour = c_lib[utils.config["font_colour"]]
    half_colour = colour(0x4a49)
    buffer.fill(bg_colour)
    co2_ppm = str(int(readings[0]))
    pad_len = max(0, 4 - len(co2_ppm))
    pad = "0" * pad_len
    co2_ppm = " " * pad_len + co2_ppm
    draw_plot = True
    if utils.config["24hr"] == False:
        c_time[0] = int(c_time[0])
        if 21 >= c_time[0] >= 12:
            time_id = "pm"
            c_time[0] = "0" + str(c_time[0] - 12)
        elif c_time[0] > 21:
            time_id = "pm"
            c_time[0] = str(c_time[0] - 12)
        else:
            time_id = "am"
    else:
        time_id = "  "
        
    if utils.config["celsius"] == "C":
        if readings[1] is None:
            temperature = "--.- C"
        else:
            temperature = f"{round(readings[1], 1)} C"
    else:
        if readings[1] is None:
            temperature = "--.- F"
        else:
            temperature = f"{fahrenheit(readings[1])} F"
            
    if readings[2] is None:
        humidity = "--.-"
    else:
        humidity = str(round(readings[2], 1))

    if state[0] != "main":
        draw_plot = False
    else:
        draw_plot = True
        
    #Standard display, big ppm, big graph
    if main_state == 0:
        font.text(buffer, f"{c_time[0]}:{c_time[1]}:{c_time[2]}{time_id} {temperature}", 10, 10, 3, font_colour)
        font.text(buffer, f"{co2_ppm}ppm", 10, 39, 6, font_colour)
        if utils.config["leading_zeros"]:
            font.text(buffer, f"{pad}", 10, 39, 6, half_colour)
        if utils.config["graph"]:
            draw_graph(buffer, graph_data, 5, 90, 310, 145, draw_plot)
            
    elif main_state == 1:
        font.text(buffer, f"{c_time[0]}:{c_time[1]}:{c_time[2]}{time_id} {temperature}", 10, 10, 3, font_colour)
        font.text(buffer, f"           {humidity}%", 10, 34, 3, font_colour)
        font.text(buffer, f"{co2_ppm}", 31, 80, 12, font_colour)
        if utils.config["leading_zeros"]:
            font.text(buffer, f"{pad}", 31, 80, 12, half_colour)
        font.text(buffer, "ppm CO2", 150, 180, 4, font_colour)
        
    elif main_state == 2:
        draw_graph(buffer, graph_data, 5, 5, 310, 230, draw_plot)
        
    else:
        font.text(buffer, "Page_state error", 10, 10, 2, font_colour)
        
    await asyncio.sleep(0)
    if state[0] == "settings" or state[0] == "settings_adj" or state[0] == "adjust":#Draw settings menu
        buffer.rect(20, 20, 320 - 2 * 20, 240 - 2 * 20, bg_colour, True)
        buffer.rect(20, 20, 320 - 2 * 20, 240 - 2 * 20, font_colour, False)
        if state[0] == "settings":
            font.text(buffer, "Settings", 30, 25, 1, font_colour)
        else:
            font.text(buffer, "Settings - Adjust", 30, 25, 1, font_colour)
        s_page_sizes = (6, 9, 1)
        if state[0] != "settings":
            page = conv_scroll(state[1])
        else:
            page = state[1]
        font.text(buffer, f"{page + 1}/3", 300 - 27, 25, 1, font_colour)
        nav_keys = ("Up    ", "Down  ", "Close ", "Adjust") if state[0] == "settings" else (("Up    ", "Down  ", "Back  ", "Adjust") if state[0] == "settings_adj" else ("Next  ", "Prev  ", "Cancel", "Set"))
        
        font.text(buffer, f"A:{nav_keys[0]}  B:{nav_keys[1]}  X:{nav_keys[2]}  Y:{nav_keys[3]}", 30, 215 - 8, 1, font_colour)
        #Settings layout
        pages = utils.pages
        if page != 2:
            debug_colour = BLUE if font_colour != BLUE else YELLOW
            for ix, key in enumerate(pages[page]):
                active = state[1] - sum(s_page_sizes[0:page]) == ix
                if active and state[0] != "settings":
                    font.text(buffer, f"{utils.setting_names[key]}", 30, 45 + 12 * ix, 1, debug_colour)
                else:
                    font.text(buffer, f"{utils.setting_names[key]}", 30, 45 + 12 * ix, 1, font_colour)
                    
                if state[0] == "adjust" and active:
                    font.text(buffer, f"{str(temp_setting)}", 250, 45 + 12 * ix, 1, debug_colour)
                else:
                    font.text(buffer, f"{str(utils.config[key])}", 250, 45 + 12 * ix, 1, font_colour)
        else:
            for ix, text in enumerate(pages[page]):
                font.text(buffer, f"{text}", 30, 45 + 12 * ix, 1, font_colour)  
        
        
def conv_scroll(x, page_sizes = (6, 9, 1)):
    x += 1
    for y, p_size in enumerate(page_sizes):
        if x <= p_size:
            return y
        else:
            x = x - p_size
    return(len(page_sizes) - 1)
    
    
async def navigate(set_state, get_values):
    global temp_setting
    global main_state
    active_set = None
    poss_setting = []
    setting_idx = 0
    press = False
    while True:
        menu_state = get_values()[2]
        s_page_sizes = (6, 9, 1)
        if press:
            if button_x.value() == 0 or button_y.value() == 0 or button_a.value() == 0 or button_b.value() == 0:
                await asyncio.sleep(0.1)
                continue
            
        press = False
        if button_x.value() == 0:
            press = True
            if menu_state[0] == "main":
                set_state(["settings", 0])
            elif menu_state[0] == "settings_adj":
                set_state(["settings", conv_scroll(menu_state[1])])
            elif menu_state[0] == "adjust":
                set_state(["settings_adj", menu_state[1]])
                active_set = None
                temp_setting = "Err"
            else:
                set_state(["main", main_state])
                
        if button_y.value() == 0:
            press = True
            if menu_state[0] == "settings":
                set_state(["settings_adj", sum(s_page_sizes[0:menu_state[1]])])
            elif menu_state[0] == "settings_adj": #Get Current Setting
                pages = utils.pages
                p_num = conv_scroll(menu_state[1])
                ix = menu_state[1] - sum(s_page_sizes[0:p_num])
                active_set = pages[p_num][ix]
                temp_setting = utils.config[active_set]
                poss_setting = utils.setting_values[active_set]
                setting_idx = poss_setting.index(temp_setting)
                set_state(["adjust", menu_state[1]])
            elif menu_state[0] == "adjust":
                utils.update_cfg(active_set, temp_setting)
                set_state(["settings_adj", menu_state[1]])
                active_set = None
                temp_setting = "Err"
                
        if button_b.value() == 0:
            press = True
            if menu_state[0] == "main" or menu_state[0] == "settings":
                max_scroll = 3
            elif menu_state[0] == "adjust":
                max_scroll = len(poss_setting)
            else:
                max_scroll = 16
            
            if menu_state[0] != "adjust":
                menu_state[1] = (menu_state[1] + 1) % max_scroll
            else:   
                setting_idx = (setting_idx + 1) % max_scroll
                temp_setting = poss_setting[setting_idx]
            
        if button_a.value() == 0:
            press = True
            if menu_state[0] == "main" or menu_state[0] == "settings":
                max_scroll = 3
            elif menu_state[0] == "adjust":
                max_scroll = len(poss_setting)
            else:
                max_scroll = 16
                
            if menu_state[0] != "adjust":
                menu_state[1] = (menu_state[1] - 1) % max_scroll
            else:
                setting_idx = (setting_idx - 1) % max_scroll
                temp_setting = poss_setting[setting_idx]
                
        if menu_state[0] == "main":
            main_state = menu_state[1]
                
        await asyncio.sleep(0.1)
    
    
async def main():
    global last_reading
    co2 = last_reading
    humidity = None
    temperature = None
    data = []
    menu_state = ["main", 0]
    ctr = 0
    
    args = [[co2, temperature, humidity], data, menu_state]
    
    def get_values():
        return(args)
    
    
    def set_state(state = ["main", 0]):
        args[2] = state
        return
    
    draw_task = asyncio.create_task(render(program_draw, get_values))
    io_task = asyncio.create_task(navigate(set_state, get_values))
    
    while True:
        co2, temperature, humidity = await read_sensor()
        if last_reading != 0:
            last_reading, co2 = co2, (co2 + last_reading) / 2
        args[0] = (co2, temperature, humidity)
        ctr += 1
        c_time = time.time()
        
        if len(data) < 50:
            data.append((int(args[0][0]), c_time))
            ctr = 0
        else:
            if c_time - data[0][1] > 240 * 60 * 60:
                data.pop(0)
                data.append((int(args[0][0]), c_time))
                ctr = 0
            elif (5 * ctr) > (c_time - data[0][1]) // 50:
                data.pop(1)
                data.append((int(args[0][0]), c_time))
                ctr = 0
        args[1] = data
    
def parse_time():
    _, _, _, _, hour, minute, second, _ = machine.RTC().datetime()
    if int(hour) < 10:
        hour = "0" + str(hour)
    if int(minute) < 10:
        minute = "0" + str(minute)
    if int(second) < 10:
        second = "0" + str(second)
    return [hour, minute, second]
    
    
def push_frame():
    global push_ready
    global state
    
    with lock:
        push_ready = False
        lcd.update()
        push_ready = True
    
    
async def render(draw_fn, draw_args, mode = "run", verbose = False):
    global state
    global push_ready
    global draw_buffer
    global disp_buffer
    refresh_rate = 20
    frame_ms = 1000.0 / refresh_rate
    fps = 0
    pushed = 0
    
    if mode == "test":
        state = "test"
        if verbose:
            print("Testing Render function...")
    else:
        state = "busy"
        
    draw_buffer.fill(0x0000)
    
    while state != "off":
        sw = time.time_ns()
        
        #Push frame buffer to display
        if push_ready:
            with lock:
                disp_buffer, draw_buffer = draw_buffer, disp_buffer
                lcd.set_framebuffer(disp_buffer)
                
            _thread.start_new_thread(push_frame, ())
        #Draw next frame
        if mode == "test":
            await draw_test(draw_buffer, pushed, fps)
        else:
            await draw_fn(draw_buffer, draw_args)
            
        #Wait for display to finish updating
        while push_ready == False:
            await asyncio.sleep(0)
        
        gc.collect()
        #Delay if needed
        frame_time = max(1, (time.time_ns() - sw) // 1000000)    
        await asyncio.sleep(max(0, (frame_ms - frame_time)/1000))
        
        fps = 1000 / frame_time
        pushed += 1
        pushed = pushed % 60
        
        if verbose:
            print(f"{1000/frame_time:.1f} fps")
        
        if mode == "test" and pushed > 11:
            state = "off"
            led.set_rgb(0, 0, 0)
            if verbose:
                print("Test Complete")
        elif mode == "static" and pushed >= 2:
            state = "off"
            
    #Update state
    state = "ready"

#Program starts
init()
#asyncio.run(render(None, None, mode = "test"))
clear()
asyncio.run(main())

