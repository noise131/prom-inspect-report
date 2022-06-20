# encoding: utf-8

from datetime import datetime, timedelta
import openpyxl
import requests
import re
from GlobalConfig import GlobalConfig
import json
import tools
import excel_operation
import sys
import os



def __del_space(str1: str) -> str:
    '''
        去除字符串中空的白字符
    '''
    return re.sub('\s', '', str1)


def __prom_url_joint(host: str, port: str, promql: str, hours_ago: int = None,
                    time_diff: int = 8, minute_step: int = 5, scheme: str = 'http') -> str | list:
    '''
        prom 查询 api URL 拼接
    '''
    promql = __del_space(promql)
    # 如果有时间参数则认为是取平均数据，将每个时间点单独合并并返回存储所有时间点 url 的 list
    if hours_ago:
        now_time = datetime.now()
        url_list = []
        for h in range(0, hours_ago):
            for m in range(0, 60, minute_step):
                query_time = datetime.strftime(now_time - timedelta(hours=h + time_diff, minutes=m),
                                                '%Y-%m-%dT%H:%M:%S.0Z')
                url_list.append('{}://{}:{}/api/v1/query?query={}&time={}'.\
                    format(scheme, host, port, promql, query_time))
                # print(query_time)
        return url_list
    # 不是取平均数据直接拼接 query url
    return '{}://{}:{}/api/v1/query?query={}'.format(scheme, host, port, promql)


def prom_query(promql: str, prom_host: str, prom_port: int, result_list: list, data_mark: str = None,
                progress_stdout: bool = True, scheme: str = 'http', group_by: str = 'instance',
                data_from: str = 'value', data_labels_dict: dict = None, unit_convert: bool = False, end_symbol: str = None):
    '''
        获取瞬时数据
    '''
    query_url = __prom_url_joint(prom_host, prom_port, promql, scheme=scheme)
    print(query_url)
    response = requests.get(url=query_url, timeout=10)
    res_data: dict = json.loads(response.content.decode(encoding='utf-8'))
    # print(response.text)
    query_result_dict = {}
    # start_time = time.perf_counter()
    print('开始扫描 : \"{}\", promql : \"{}\"'.format(data_mark, promql))
    for series in res_data.get('data').get('result'):
        metric: dict = series.get('metric')
        value: list = series.get('value')
        instance = metric.get('instance')
        instance = tools.instance_handel(instance)
        if type(query_result_dict.get(instance)) is not dict:
            query_result_dict[instance] = {}
            query_result_dict[instance]['主要 IP 地址'] = instance
        if data_from == 'value':
            value_handle = value[-1]
            if re.findall(r'\.', value[-1]):
                try:
                    value_handle = str(round(float(value[-1]),1))
                except Exception:
                    print(type(value[-1]))
                    value_handle = value[-1]
            # value_handle = round(value[-1], 1) if type(value[-1]) is float else value[-1]
            if unit_convert:
                tmp_dict = tools.unit_convert(value[-1])
                value_handle = '{} {}'.format(tmp_dict.get('size'), tmp_dict.get('unit'))
            if end_symbol:
                value_handle = '{} {}'.format(value_handle, end_symbol)
            query_result_dict[instance][data_mark] = value_handle
            continue
        for label_k, label_v in data_labels_dict.items():
            query_result_dict[instance][label_k] = metric.get(label_v)

    result_list.append(query_result_dict)
    print('\"{}\" 扫描完成'.format(data_mark), end='\n\n')


def prom_query_interval(promql: str, prom_host: str, prom_port: int, result_list: list,
                        hours_ago: str, minute_step: int = 5, data_mark: str = None, time_diff: int = 8, progress_stdout: bool = True,
                        group_by: str = 'instance', scheme: str = 'http', unit_convert: bool = False, end_symbol: str = None):
    '''
        获取区间平均数据
    '''
    print(promql)
    print('开始扫描 : \"{}\", promql : \"{}\" --- 区间类型数据'.format(data_mark, promql))
    query_url_list = __prom_url_joint(prom_host, prom_port, promql, hours_ago, time_diff=time_diff, minute_step=minute_step, scheme=scheme)
    # for i in query_url_list:
    #     print(i)
    all_result_dict: dict = {}
    for query_url in query_url_list:
        response = requests.get(url=query_url, timeout=10)
        res_data: dict = json.loads(response.content.decode(encoding='utf-8'))
        for series in res_data.get('data').get('result'):
            metric: dict = series.get('metric')
            value: list = series.get('value')
            instance = metric.get('instance')
            instance = tools.instance_handel(instance)
            if not all_result_dict.get(instance):
                all_result_dict[instance] = []
            all_result_dict[instance].append(round(float(value[-1]), 1))
    final_result_dict = {}
    for instance in all_result_dict.keys():
        sum = 0
        # 循环列表
        final_result_dict[instance] = {}
        for value in all_result_dict.get(instance):
            sum += value
        avg_usage = round(sum / len(all_result_dict.get(instance)), 1)
        if end_symbol:
                avg_usage = '{} {}'.format(avg_usage, end_symbol)
        final_result_dict[instance][data_mark] = avg_usage
    result_list.append(final_result_dict)
    print('\"{}\" 扫描完成'.format(data_mark), end='\n\n')
    # print(all_result_dict)


def dict_merge(*args: dict) -> dict:
    merge_dict = {}
    for dict_element in args:
        for k, v in dict_element.items():
            # print(type(merge_dict.get(k)), type(v), type(merge_dict.get(k)) is not type(v))
            if not v:
                print('字典 : {}, key : {} 下的值为空或是None'.format(dict_element, k))
                if not merge_dict.get(k):
                    merge_dict[k] = v
                continue
            if not merge_dict.get(k):
                merge_dict[k] = v
                continue
            if type(merge_dict.get(k)) is not type(v):
                print('两个字典相同 key 下的值类型不同, 无法合并')
                continue
            # v 是一个字典时进行轮询合并
            for v_k, v_v in v.items():
                merge_dict[k][v_k] = v_v
    return merge_dict




if __name__ == '__main__':
    collect_config: dict = {
        '资产清单+节点基本资源巡检_日巡报告': {
            'node_info': {
                'data_mark': 'node_info',
                'promql': 'node_uname_info{}',
                'data_from': 'metric',
                'labels_dict': {'主机名': 'nodename', '内核': 'release', '系统类型': 'sysname'},
                'labels_titel_dict': {'hostname': '主机名', 'kernel': '内核', 'system_type': '系统类型'}
            },
            'system_info': {
                'data_mark': 'system_info',
                'promql': 'node_os_info{}',
                'data_from': 'metric',
                'labels_dict': {'系统名': 'name', '系统版本': 'version'},
                'labels_titel_dict': {'sys_name': '系统名', 'sys_version': '系统版本'}
            },
            'cpu_core_total': {
                'data_mark': 'cpu_core_total',
                'data_mark_titel': 'CPU 总核心数',
                'promql': 'count(node_cpu_seconds_total{mode="idle"})by(instance)',
            },
            'cpu_usage_percent_avg': {
                'data_mark': 'cpu_usage_percent_avg',
                'data_mark_titel': '24h CPU 平均使用率',
                'promql': '100-avg(rate(node_cpu_seconds_total{mode="idle"}[5m])*100)by(instance)',
                'hours_ago': 24,
                'minute_step': 5,
                'end_symbol': '%'
            },
            'mem_total': {
                'data_mark': 'mem_total',
                'data_mark_titel': '内存总容量',
                'promql': 'node_memory_MemTotal_bytes{}',
                'unit_convert': True
            },
            'mem_usage_percent_avg': {
                'data_mark': 'mem_usage_percent_avg',
                'data_mark_titel': '24h 内存平均使用率',
                'promql': '(node_memory_MemTotal_bytes-node_memory_MemAvailable_bytes)/node_memory_MemTotal_bytes*100',
                'hours_ago': 24,
                'minute_step': 5,
                'end_symbol': '%'
            },
            '/_filesys_size': {
                'data_mark': '/_filesys_size',
                'data_mark_titel': '/ 分区总容量',
                'promql': 'max(node_filesystem_size_bytes{mountpoint="/"})by(instance)',
                'unit_convert': True
            },
            '/_filesys_usage_percent': {
                'data_mark': '/_filesys_usage_percent',
                'data_mark_titel': '/ 分区使用率',
                'promql': '100-(node_filesystem_free_bytes{fstype=~"ext[0-9]|xfs",mountpoint="/"}/node_filesystem_size_bytes{fstype=~"ext[0-9]|xfs",mountpoint="/"}*100)',
                'end_symbol': '%'
            },
            '/_filesys_inode_usage_percent': {
                'data_mark': '/_filesys_inode_usage_percent',
                'data_mark_titel': '/ 分区 inode 使用率',
                'promql': '100-(node_filesystem_files_free{fstype=~"ext[0-9]|xfs",mountpoint="/"}/node_filesystem_files{fstype=~"ext[0-9]|xfs",mountpoint="/"}*100)',
                'end_symbol': '%'
            }
        }
    }

    wb = openpyxl.Workbook()
    sheet_index = 0
    sheet = None
    for sheet_k, sheet_v in collect_config.items():
        wb.create_sheet(title=sheet_k, index=sheet_index)
        sheet = wb[sheet_k]
        sheet_index += 1
        column_titel_row_list = ['主要 IP 地址']
        # data_row_list = []
        all_query_result_list = []
        for query_titel in sheet_v.keys():
            query_dict = sheet_v.get(query_titel)
            # print(query_dict)
            # column_titel_row_list.append(query_dict.get('data_mark_titel'))
            unit_convert = query_dict.get('unit_convert')
            end_symbol = query_dict.get('end_symbol')
            if query_dict.get('data_from') == 'metric':
                column_titel_row_list += query_dict.get('labels_dict')
                prom_query(query_dict.get('promql'), GlobalConfig.prom_host, GlobalConfig.prom_port, all_query_result_list, query_dict.get('data_mark'), data_from='metric', data_labels_dict=query_dict.get('labels_dict'), scheme=GlobalConfig.scheme)
            else:
                if query_dict.get('hours_ago'):
                    column_titel_row_list.append(query_dict.get('data_mark_titel'))
                    prom_query_interval(query_dict.get('promql'), GlobalConfig.prom_host, GlobalConfig.prom_port,
                        all_query_result_list, query_dict.get('hours_ago'), time_diff=GlobalConfig.time_diff, minute_step=query_dict.get('minute_step'), data_mark=query_dict.get('data_mark_titel'), scheme=GlobalConfig.scheme, end_symbol=end_symbol)
                    pass
                else:
                    column_titel_row_list.append(query_dict.get('data_mark_titel'))
                    prom_query(query_dict.get('promql'), GlobalConfig.prom_host, GlobalConfig.prom_port, all_query_result_list, query_dict.get('data_mark_titel'), scheme=GlobalConfig.scheme, unit_convert=unit_convert, end_symbol=end_symbol)
        # print(column_titel_row_list)
        sheet.append(column_titel_row_list)
        merge_dict = dict_merge(*all_query_result_list)
        # print(merge_dict)
        for row in merge_dict.values():
            data_row_list = []
            for cell_titel in column_titel_row_list:
                data_row_list.append(row.get(cell_titel))
            sheet.append(data_row_list)
        
    print('调整单元格宽度')
    excel_operation.auto_column_width(sheet)
    print('单元格宽度调整完成')

    os.chdir(sys.path[0])
    if not os.path.isdir('report_export'):
        try:
            os.remove('report_export')
        except Exception as e:
            # print(e)
            pass
        finally:
            os.mkdir('report_export')

    wb.save('report_export/prom-inspect-report_{}.xlsx'.format(datetime.now().strftime('%Y%m%dT%H%M%S')))

    