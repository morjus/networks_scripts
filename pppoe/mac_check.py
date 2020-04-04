import re
import win32clipboard
import telnetlib
from tabulate import tabulate
import keyring

def huawei_zte_finder(s):
    """
    На вход принимает список с мак-адресами.
    Адаптирует мак-адреса 0000-5e00-018b и 0000.5e00.018b в вид 50-FF-20-1A-1B-4D.
    Возвращает список с адресами.
    
    """

    mac_list = []
    for macs in s:
        mac_in_port = macs[0:2]+'-'+macs[2:4]+'-'+macs[5:7]+'-'+macs[7:9]+'-'+macs[10:12]+'-'+macs[12:14]
        mac_list.append(mac_in_port)
    return mac_list

def mac_morfer(text):
    """
    На вход принимает строку с мак-адресам.
    Ищет совпдаения с регулярками. 
    При совпадении прогоняет через функцию адаптации под синтаксис браса.
    Удаляет одинаковые маки.
    Возвращает список мак-адресов, готовых для отправки на брас.
    
    """

    dlink_bras_pattern = r'((?:\w{2}.){5}\w{2})' # regex 50-FF-20-1A-1B-4D и 50:FF:20:1A:1B:4D
    huawei_zte_pattern = r'((?:\w{4}.){2}\w{4})' # regex 0000-5e00-018b и 0000.5e00.018b  
    if re.findall(huawei_zte_pattern, text):
        res = huawei_zte_finder(re.findall(huawei_zte_pattern, text))
    elif re.findall(dlink_bras_pattern, text):
        res = re.findall(dlink_bras_pattern, text)
    else:
        res = None
    if res:
        res = list(set(res))
    return res

def mac_check(tn, mac):
    """
    На вход поступает объект подключения и мак-адрес.
    На брас поступает команда show service id 100 subscriber-hosts mac + mac-address
    На основании ответа браса принимается решение это DHCP или PPPOE сессия,
    затем устанавливается соответствующая команда.
    В ответе ищется sap lag. Если он есть функция ищет ip и затем отправляется вторая команда.
    На основании ответа и информации 


    """

    lag = ""
    mac_output = ""
    cmd_2 = ""
    uptime = ""
    login = ""

    lag_pattern = r'((?:lag\-)+(?:\d+.){2}\d+)' # regex lag-nums:nums.nums
    ips_pattern = r'((?:\d+\.){3}\d+)' # regex 192.168.11.3
    cmd_1 = 'show service id 100 subscriber-hosts mac ' + mac 
    tn.write(cmd_1.encode('ascii') + b'\r')
    tn.write(' '.encode('ascii'))
    mac_output = tn.read_until(b'n#', timeout=15).decode('ascii')
    if 'IPCP' in mac_output:
        cmd_2 = 'show service id 100 ppp session ip-address '
    elif 'DHCP' in mac_output:
        cmd_2 = 'show service id 100 dhcp lease-state ip-address '
    else:
        pass

    lag = re.findall(lag_pattern, mac_output) # for_lag
    if lag:
        lag = lag[0]
        ips = re.findall(ips_pattern, mac_output) # for_ip
        ips = ips[0]
        cmd_2 = cmd_2 + ips
        tn.write(cmd_2.encode('ascii') + b'\r')
        ip_address_output = tn.read_until(b'#', timeout=15).decode('ascii')
        result_list = ip_address_output.split('-------------------------------------------------------------------------------')

        try:
            if result_list:
                if len(result_list)==1:
                    result_list = ip_address_output.split('-------------------------------------------------------------')
                if 'IPCP' in mac_output:
                    string_for_login_uptime = result_list[1]
                    string_for_login_uptime = string_for_login_uptime.split('\r\n')
                    login = string_for_login_uptime[1]
                    string_for_uptime = string_for_login_uptime[3]
                    list_for_uptime = string_for_uptime.split('   ')
                    uptime = list_for_uptime[3].strip()
                elif 'DHCP' in mac_output:
                    login = 'DHCP HAS NO LOGIN'
                    string_for_ip_lag_uptime = result_list[1]
                    string_for_ip_lag_uptime = string_for_ip_lag_uptime.split('  ')
                    uptime = string_for_ip_lag_uptime[4]
                column = ['MAC-address:','IP client:','Uptime:','Login:','Sap lag:']
                data = [mac,ips,uptime,login,lag]
                print(tabulate(list(zip(column,data))))
        except IndexError:
            print('-------------------------------------------------------------')
            print(ip_address_output)
            print('-------------------------------------------------------------')
    else:
        print('No PPPoE session in: ' + mac)

def cut_from_clipboard():
    """
    Ожидает текстовые данные с мак-адресами на входе.
    Вырезает содержимое буфера обмена. Возвращает строку с данными.
    
    """

    win32clipboard.OpenClipboard()
    text = win32clipboard.GetClipboardData()
    win32clipboard.EmptyClipboard()
    win32clipboard.CloseClipboard()
    return text

def login(user,passw,host):
    """
    Принимает на вход логин, пароль, адрес подключения.
    Подключается, авторизуется и возвращает переменную, содержащую текущее соединение.
    
    """

    try:
        telnetconnect = telnetlib.Telnet()
        telnetconnect.open(host, 23, 5)
        telnetconnect.read_until(b'Login: ')
        telnetconnect.write(user.encode('ascii') + b'\r')
        telnetconnect.read_until(b'Password: ')
        telnetconnect.write(passw.encode('ascii') + b'\r')
        login_mes = telnetconnect.read_until(b'#', timeout=5).decode('ascii')
        if 'bsr01-kzn#' in login_mes:
            print('\nLogin in BRAS okay!\n')
            return telnetconnect
    except Exception as error:
        print('Something wrong with login fucn:', error)

if __name__ == '__main__':
    USER = "khusainov.if" # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    HOST = keyring.get_password("bras", USER) # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    mac_list = mac_morfer(cut_from_clipboard())
    tn = login(USER,PASSWORD,HOST)

    while mac_list:
        print(mac_list) # list of catched mac-addreses
        tn.write(b'\r')
        login_ok = tn.read_until(b'#', timeout=5).decode('ascii')
        if keyring.get_password("host_response", "khusainov.if") in login_ok: # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
            print('-----------------------\nStill connected to BRAS\n-----------------------')
            for mac in mac_list: #check mac
                map(mac_check(tn, mac), mac_list)
            choice = input('Done!\nMake a choice:\n[y for get MACs from clipboard] or ["Enter" for close]: ')
            if choice == 'y':
                mac_list = mac_morfer(cut_from_clipboard())
                continue
            else:
                print('Closing...')
                tn.close()
                break 
        else:
            print('Bras is broken or wrong login/password.')
            recon_mes = input('Try to reconnect? [y for rc] or ["Enter" for close]:')
            if recon_mes == 'y':
                tn = login(USER,PASSWORD,HOST)
                continue
            else:
                print('Closing...')
                tn.close()
                input(f'Press "Enter" to close.')
                break 
    else:
        print('Bad input. Closing...')
        tn.close()
        input(f'Press "Enter" to close.')