# encoding: utf-8

import time


def instance_handel(instance: str) -> str:
    # instance = instance[:instance.index(':')] if ':' in instance else instance
    if ':' in instance:
        instance = instance[:instance.index(':')]
    return instance


def progress(start_time:float, info: str, current: int, end: int):
    '''
        打印进度信息
    '''
    time_dur = time.perf_counter() - start_time
    speed = round(current / end * 100)
    if speed != 100:
        print('\r{} : {}% --- {:.2f}'.format(info, speed, time_dur), end='')
        return
    print('\r{} : {}% --- {:.2f}'.format(info, speed, time_dur))


def unit_convert(size: int) -> dict[int, str]:
    '''
        数据单位转换 (将字节单位数据按进制向上转换)
    '''
    try:
        size = int(size)
    except ValueError:
        return {"status": False, "code": 1, "info": 
                "数据 : {} 不合法, 无法转换".format(size)}
    unit_dict = {
        1: "B", 2: "KiB", 3: "MiB",
        4: "GiB", 5: "TiB", 6: "PiB",
        7: "EiB", 8: "ZiB", 9: "YiB"
    }
    unit_index = 1
    while True:
        if size >= 1024 and unit_index != 9:
            size /= 1024
            unit_index += 1
        else:
            return {"size": round(size, 1), "unit": unit_dict.get(unit_index)}
