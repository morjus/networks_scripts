import csv
from jinja2 import Environment, FileSystemLoader
import yaml
import re
import xlrd
import os
import fileinput
import sys
import shutil
from ipaddress import ip_address
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

models = {
    '1': 'HUAWEI S5320-28P-LI-AC',
    '2': 'TP-Link T2600G',
    # '3': 'D-Link 1210',
    # '4': 'D-link 3028/1228',
    # '5': 'Eltex',
    # '6': 'Maipu'
}

items = []  # Для списка с IP
full_yaml_file = []  # Для финального файла с yaml данными
legend = {
    'а': 'a',
    'б': 'b',
    'в': 'v',
    'г': 'g',
    'д': 'd',
    'е': 'e',
    'ё': 'yo',
    'ж': 'zh',
    'з': 'z',
    'и': 'i',
    'й': 'y',
    'к': 'k',
    'л': 'l',
    'м': 'm',
    'н': 'n',
    'о': 'o',
    'п': 'p',
    'р': 'r',
    'с': 's',
    'т': 't',
    'у': 'u',
    'ф': 'f',
    'х': 'h',
    'ц': 'ts',
    'ч': 'ch',
    'ш': 'sh',
    'щ': 'shch',
    'ъ': 'y',
    'ы': 'y',
    'ь': "",
    'э': 'e',
    'ю': 'yu',
    'я': 'ya',

    'А': 'A',
    'Б': 'B',
    'В': 'V',
    'Г': 'G',
    'Д': 'D',
    'Е': 'E',
    'Ё': 'YO',
    'Ж': 'ZH',
    'З': 'Z',
    'И': 'I',
    'Й': 'Y',
    'К': 'K',
    'Л': 'L',
    'М': 'M',
    'Н': 'N',
    'О': 'O',
    'П': 'P',
    'Р': 'R',
    'С': 'S',
    'Т': 'T',
    'У': 'U',
    'Ф': 'F',
    'Х': 'H',
    'Ц': 'TS',
    'Ч': 'CH',
    'Ш': 'SH',
    'Щ': 'SHCH',
    'Ъ': 'Y',
    'Ы': 'Y',
    'Ь': "",
    'Э': 'E',
    'Ю': 'YU',
    'Я': 'YA',
}


def latinizator(letter, dic):
    """
    Замена кириллицы в тексте на латиницу.

    """

    for i, j in dic.items():
        letter = letter.replace(i, j)
    return letter


def check_ip(ip):
    """
    Проверка корректности написанного IP-адреса. 

    """

    try:
        ip_address(ip)
    except ValueError:
        return False
    else:
        return True


def transliterator(file):
    """
    На вход поступает имя файла или путь до него.
    Функция транслитерирует файл, раскладывает файл в список через ' ', собирает через _

    """

    with fileinput.FileInput(file, inplace=True, backup='.bak') as f:
        for line in f:
            line = line.upper()
            name_list = line.split(' ')
            line = '_'.join(name_list)
            print(latinizator(line, legend), end='')


def csv_from_excel(table):
    """
    На вход поступает таблица формата xls или xlsx.
    Возвращает эту таблицу в формате csv.

    """

    wb = xlrd.open_workbook(table)
    sh = wb.sheet_by_index(0)
    result = script_files_path + 'result.csv'
    with open(result, 'w') as res:
        wr = csv.writer(res, lineterminator='\r', quoting=csv.QUOTE_ALL)
        for rownum in range(sh.nrows):
            wr.writerow(sh.row_values(rownum))

    return result


def convert_switch_data_to_dict(line):
    """
    На вход поступает список вида:
    ['TATARSTAN_9', '32768.0', '10.246.213.44', '1030-1053', '299.0']
    Превращает это в словарь вида:
    10.246.213.44:{'HOSTNAME': 'TATARSTAN_9',
            'STP': '32768',
            'IP': '10.246.213.44,
            'GATEWAY': '10.246.213.1',
            'MGMT': '299',
            'access_ports': {1: 1060, ... 14: 1073, ... 24: 1083},
            'B2B_VLAN':'200'}
    Затем сохраняет его в виде yaml.
    Возвращает список IP.

    """
    list_line = []
    list_line = line[3].split('-')
    ranger = list(range(int(list_line[0]), int(list_line[1])+1))
    ports = list(range(1, 25))
    acc_dict = dict(zip(ports, ranger))
    HOSTNAME = line[0]
    STP = int(float(line[1]))
    IP = line[2]
    gateway_list = IP.split('.')
    GATEWAY = gateway_list[0] + '.' + \
        gateway_list[1] + '.' + gateway_list[2] + '.1'
    MGMT = int(float(line[4]))

    if check_ip(IP):
        item = {
            'HOSTNAME': HOSTNAME,
            'STP': STP,
            'IP': IP,
            'GATEWAY': GATEWAY,
            'MGMT': MGMT,
            'access_ports': acc_dict,
            'B2B_VLAN': int(str(MGMT)[0]+'00')
        }
        full_yaml_file.append(item)
        items.append(item['IP'])
        yaml_data_path = script_files_path + 'full_yaml'
        with open(yaml_data_path, 'w') as final:
            final.write(yaml.dump(full_yaml_file,
                                  default_flow_style=False, allow_unicode=True))
    else:
        print(f'{IP} is wrong. Please check your xls table for correct values of IPs.')
        pass
    return items


def converter(file):
    """
    Конвертирует ФАЙЛ CSV в YAML.
    Попутно считает строчки, чтобы выдать ошибку с номером строки, если не удастся сформировать данные из строки.

    """

    with open(file, 'r') as source: 
        reader = csv.reader(source)
        next(reader)
        s = list(reader)
        count = 1
        for switch_data in s:
            count += 1
            try:
                list_of_ip = convert_switch_data_to_dict(switch_data)
            except ValueError:
                print(f'{count} row is empty or wrong.')
    return list_of_ip


def config_maker(ip):
    """
    Принимает на вход IP-адрес (причем yaml файл для конфигурации уже должен существовать),
     добавляет к этому IP .yaml, а затем генерирует конфиг.

    """

    yaml_data_path = script_files_path + 'full_yaml'
    if model == 'HUAWEI S5320-28P-LI-AC':  # huawei
        env = Environment(loader=FileSystemLoader(
            'TEMPLATES\\HUAWEI S5320-28P-LI-AC'))
        if b2b == '2':
            template = env.get_template('template_uno.txt')
        else:
            template = env.get_template('template.txt')
    elif model == 'TP-Link T2600G':  # tp-link
        env = Environment(loader=FileSystemLoader(
            'TEMPLATES\\TP-Link_T2600G'))
        if b2b == '2':
            template = env.get_template('template_uno.txt')
        else:
            template = env.get_template('template.txt')
    with open(yaml_data_path) as full:
        switches = yaml.safe_load(full)
    for switch in switches:
        config_name = switch['IP'] + '.cfg'
        address = switch['HOSTNAME']
        address = re.findall(
            r'([a-zA-Z]+\_+\d+|[a-zA-Z]+\_[a-zA-Z]+\_+\d+)', address)
        address = address[0]
        new_path = dir_maker(address, model)
        config_path = new_path + '\\' + config_name

        with open(config_path, 'w') as f:
            f.write(template.render(switch))


def model_choicer(model):
    """
    На основании выбора 1 или 2 возвращает модель для дальнейшего выбора шаблона конфигурации.
    """

    if model == '1':
        return 'HUAWEI S5320-28P-LI-AC'
    elif model == '2':
        return 'TP-Link T2600G'
    else:
        print('Unknown model.')


def dir_maker(address, model):
    """
    Создаёт директории адресам, а затем по моделям коммутаторов. 

    """

    current_dir = os.getcwd()  # Адрес текущей директории
    path_for_address = '\\' + address
    path_for_model = '\\' + model
    result = '\\RESULT'
    path = current_dir + result + path_for_address + path_for_model

    try:
        os.makedirs(path)
    except Exception:
        pass
    finally:
        return path


def script_files():
    """
    Создаёт папку для файлов, которые генерятся в процессе работы скрипта. Затем они удаляются. 

    """

    current_dir = os.getcwd()
    path_for_res = current_dir + '\\script_files'
    try:
        os.makedirs(path_for_res)
    except Exception as error:
        print(f'script_files error: {error}')
    return path_for_res


if __name__ == '__main__':

    while True:
        table_of_switches = input('Enter filename: ')
        if os.path.exists(table_of_switches):
            b2b = str(input('For common enter 1\nFor b2b enter 2\nEnter:'))
            for k, v in models.items():
                print(f'To make {v} configuration enter {k}')
            switch_model = input("Enter: ")
            script_files_path = script_files() + '\\'

            model = model_choicer(str(switch_model))
            csv_file_path = csv_from_excel(table_of_switches)
            transliterator(csv_file_path)
            ip_list = converter(csv_file_path)

            pool = ThreadPool(2)
            pool.map(config_maker, ip_list)
            pool.close()
            pool.join()
            # Удаляет файлы, которые генерятся в процессе работы
            shutil.rmtree(script_files_path)
            input("Done. Press 'Enter' for exit.")
            break
        else:
            print(f'"{table_of_switches}" is not found!\n')
