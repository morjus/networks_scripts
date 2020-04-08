from switch_management_refactoring import *
from time import gmtime, strftime


def ip_port_vlan_getter(path_to_ips):
    """
    На вход поступает путь до текстового файла с ожидаемыми строками вида: 
    10.246.18.10 2
    10.246.18.3 3
    10.246.18.7 Ethernet0/0/10

    Возвращает ip, port, vlan.

    """
    result = []
    with open(path_to_ips, "r") as filename:
        for line in filename:
            ip = line.split()[0]
            port = line.split()[1]
            port_pvids = snmp_get_next(ip, '1.3.6.1.2.1.17.7.1.4.5.1.1')
            if 'th' in port:
                number_of_port = port.split("/")[-1]
                vlan = port_pvids[number_of_port]
            else:
                vlan = port_pvids[port]
            result.append((ip, port, vlan))
    return result


def command_maker(model, port, vlan=None):
    """
    Принимает на вход объект соединения, модель, порт.
    На основании модели принимает решение откуда брать шаблоны команд.
    Генерит команды.
    Отправляет на коммутатор.

    """
    commands_for_write = []
    commands_template = None

    if "D-Link" in model:
        if "DES-1210-28" in model["D-Link"]:
            with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\commands_dlink_1210.txt", "r") as filename:
                commands_template = filename.readlines()
        else:
            with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\commands_dlink.txt", "r") as filename:
                commands_template = filename.readlines()
    elif "Huawei" in model:
        with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\commands_huawei.txt", "r") as filename:
            commands_template = filename.readlines()

    for command in commands_template:
        if "<VLAN>" in command:
            command = command.replace("<VLAN>", str(vlan))
        elif "<PORT>" in command:
            command = command.replace("<PORT>", str(port))
        commands_for_write.append(command)

    return commands_for_write


def main(ip, port, pvid):

    USER = 'khusainov.if'
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")
    try:
        if ip_ping_checker(ip):
            print(ip + ' ' + 'START')
            with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\log.txt", "a") as log:
                log.write(ip + ' ' + 'START ' + strftime("%d-%m-%Y %H:%M:%S", gmtime()) + '\n')
            tn, data = full_connection(USER, PASSWORD, ip)
            commands_for_write = command_maker(data, port, vlan=pvid)
            tn, error = command_writer(tn, data, commands=commands_for_write)
            if error != None:
                print("Error in main():", str(error))
                with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\log.txt", "a") as log:
                    log.write(ip + ' FAIL ' + strftime("%d-%m-%Y %H:%M:%S", gmtime()) + '\n')
                    log.write(ip + ' ' + str(error) + '\n')
            else:
                print(ip + ' ' + 'OK')
                with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\log.txt", "a") as log:
                    log.write(ip + ' ' + 'OK ' + strftime("%d-%m-%Y %H:%M:%S", gmtime()) + '\n')
    except Exception as error:
        print("Error in main():", error)
        with open("C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\log.txt", "a") as log:
                log.write(ip + ' FAIL ' + strftime("%d-%m-%Y %H:%M:%S", gmtime()) + '\n')
                log.write(ip + ' ' + str(error) + '\n')
    finally:
        end_connection(data, tn)
        tn.close()


if __name__ == "__main__":
    switches = ip_port_vlan_getter(
        "C:\\Users\\ifkhu\\dev\\python_projects\\ready\\iptv_changer\\ips.txt")
    #print(switches)
    for switch in switches:
        ip, port, vlan = switch
        main(ip, port, vlan)
    #print(ip, port, vlan)
    #
