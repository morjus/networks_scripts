import time
from selenium import webdriver as wb
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def browser():
    print("\nstart browser for make OMNY..")
    browser = wb.Chrome()
    return browser

link = "http://10.90.239.141/"
uname = "admin"
def_passw = "yabdeaps"


def login(browser, passw):
    '''
    Логинится на страницу.
    '''
    browser.get(link)
    login = browser.find_element(By.CSS_SELECTOR, "#input_user_name_text")
    login.send_keys(uname)
    password = browser.find_element(By.CSS_SELECTOR, "#input_password_text")
    password.send_keys(passw)
    button = browser.find_element(By.CSS_SELECTOR, "#button_login_ipcweb")
    button.click()
    return browser

def go_to_options(browser):
    '''
    Переходит на страницу настроек.
    '''
    option_page = browser.find_element(By.CSS_SELECTOR, "#div_configuration")
    option_page.click()
    return browser

def go_to_time(browser):
    '''
    Переходит на страницу с установкой времени.
    '''
    system_options = browser.find_element(By.CSS_SELECTOR, "#pmenu_system")
    system_options.click()
    datetime_menu = browser.find_element(By.CSS_SELECTOR, "#div_submenu_item_datetime.cls_submenu_items_text")
    browser.execute_script("arguments[0].setAttribute('class','cls_submenu_items_text cls_submenu_item_selected')", datetime_menu)
    time.sleep(1)
    datetime_menu.click()
    #time.sleep(10)
    #browser.find_element(By.CSS_SELECTOR, '#div_children_page_area')
    '''
    execute_script("document.getElementById('allImages').value = '../uploads/b31f8a31-9d4e-49a6-b613-fb902de6a823.jpg';")
    Открыто: #div_submenu_item_datetime.cls_submenu_items_text cls_submenu_item_selected
    Закрыто: #div_submenu_item_datetime
     '''
    #datetime_menu = browser.find_element(By.CSS_SELECTOR, "#pmenu_sub_datetime")
    #datetime_menu.click()
    return browser

def set_time(browser):
    '''
    Ставит галку в чекбоксе синхронизации с NTP сервером.
    Устанавливает ip NTP.
    Сохраняет настройки.
    '''
    subframe = browser.find_element(By.CSS_SELECTOR, '#frame_subpage')
    browser.switch_to_frame(subframe)
    wait = WebDriverWait(browser,15)
    wait.until(EC.visibility_of_element_located((By.ID, "button_devicetime_save")))
    #browser.find_element(By.CSS_SELECTOR, '[src^="subpages/datetime"]')
    #time.sleep(10)
    #browser.switch_to_default_content()
    manual_time = browser.find_element(By.CSS_SELECTOR, '#input_manual_date')
    browser.execute_script("arguments[0].setAttribute('disabled','disabled')", manual_time)
    '''
    time.sleep(1)
    checkbox = browser.find_element(By.CSS_SELECTOR, '[for="input_ntp_enable"]') #[for="input_ntp_enable"]
    time.sleep(1)
    checkbox.click()#label_manual_set
    time.sleep(1)
    '''
    input_ntp_ip = browser.find_element(By.CSS_SELECTOR, "#input_ntp_server_addr")
    input_ntp_ip.clear()
    input_ntp_ip.click()
    input_ntp_ip.send_keys("109.194.177.5")
    save_button = browser.find_element(By.CSS_SELECTOR, "#button_devicetime_save")
    save_button.click()
    browser.switch_to_default_content()
    return browser


def set_new_admin_password_on_security_page(browser, admin_pass):
    '''
    Кликает на "Безопасность". 
    Кликает на "Управление пользователями" 
    Кликает на пользователя admin.
    Кликает на Изменить.
    Вписывает новый пароль.
    Подтверждение нового пароля.
    Кликает сохранить.
    Затем нужно снова логиниться
    '''
    security_options = browser.find_element(By.CSS_SELECTOR, "#pmenu_security")
    security_options.click()
    security_menu = browser.find_element(By.CSS_SELECTOR, "#div_submenu_item_manageuser.cls_submenu_items_text")
    browser.execute_script("arguments[0].setAttribute('class','cls_submenu_items_text cls_submenu_item_selected')", security_menu)
    time.sleep(1)
    security_menu.click()

    subframe = browser.find_element(By.CSS_SELECTOR, '#frame_subpage')
    browser.switch_to_frame(subframe)
    wait = WebDriverWait(browser,15)
    wait.until(EC.visibility_of_element_located((By.ID, "button_usermanage_modify")))

    select_row = browser.find_element(By.CSS_SELECTOR,"#table_row_0")
    browser.execute_script("arguments[0].setAttribute('class','cls_usermanage_list_item_size cls_usermanage_list_row_selected')", select_row)
    row_click = browser.find_element(By.CSS_SELECTOR, '.cls_usermanage_list_item')
    row_click.click()
    time.sleep(1)
    button = browser.find_element(By.ID, "button_usermanage_modify").click()
    wait.until(EC.visibility_of_element_located((By.ID, "button_usermanage_dialog_save")))
    passw_input = browser.find_element(By.ID, "input_usermanage_password_text")
    passw_input.click()
    time.sleep(1)
    passw_input.send_keys(admin_pass)
    passw_confirm = browser.find_element(By.ID, "input_usermanage_confirm_text")
    passw_confirm.click()
    time.sleep(1)
    passw_confirm.send_keys(admin_pass)
    button = browser.find_element(By.ID, "button_usermanage_dialog_save")
    button.click()
    time.sleep(1)
    browser.switch_to_default_content()

    login = browser.find_element(By.CSS_SELECTOR, "#input_user_name_text")
    login.clear()
    login.send_keys(uname)
    password = browser.find_element(By.CSS_SELECTOR, "#input_password_text")
    password.send_keys(admin_pass)
    button = browser.find_element(By.CSS_SELECTOR, "#button_login_ipcweb")
    button.click()
    return browser

def set_pppoe_login_password(browser, login, passw):
    '''
    Кликает на "Сеть".
    Кликает на "PPPoE"
    Кликает на чекбокс "Включить PPPoE"
    Вводит Имя пользователя
    Вводит пароль 
    Нажимает сохранить.
    '''
    netowork_options = browser.find_element(By.CSS_SELECTOR, "#pmenu_network")
    netowork_options.click()
    pppoe_menu = browser.find_element(By.CSS_SELECTOR, "#div_submenu_item_pppoe.cls_submenu_items_text")
    browser.execute_script("arguments[0].setAttribute('class','cls_submenu_items_text cls_submenu_item_selected')", pppoe_menu)
    time.sleep(1)
    pppoe_menu.click()

    subframe = browser.find_element(By.CSS_SELECTOR, '#frame_subpage')
    browser.switch_to_frame(subframe)
    wait = WebDriverWait(browser,15)
    wait.until(EC.visibility_of_element_located((By.ID, "button_pppoe_save")))
    pppoe_checkbox = browser.find_element(By.ID, 'check_enable_pppoe')
    #pppoe_checkbox.click()

    pppoe_login = browser.find_element(By.ID, 'input_user_name')
    pppoe_login.clear()
    pppoe_login.click()
    pppoe_login.send_keys(login)
    pppoe_password = browser.find_element(By.ID, 'input_password')
    pppoe_password.clear()
    pppoe_password.click()
    pppoe_password.send_keys(passw)

    save_button = browser.find_element(By.ID, 'button_pppoe_save')
    #save_button.click()
    browser.switch_to_default_content()
    return browser

def set_video_options(browser):
    '''
    Кликает на Видео & Аудио. 
    Кликает на OSD
    Убирает чекбокс с "Показывать модель устройства"
    Кликает "Сохранить"
    Кликает "Видео"
    Устанавливает разрешение главного потока 1280х720
    Убирает чекбоксы "Включить аудио" с обоих потоков.
    Нажимает сохранить
    '''
    audio_video_options = browser.find_element(By.CSS_SELECTOR, "#pmenu_audio_video")
    audio_video_options.click()
    OSD = browser.find_element(By.CSS_SELECTOR, "#div_submenu_item_osd.cls_submenu_items_text")
    browser.execute_script("arguments[0].setAttribute('class','cls_submenu_items_text cls_submenu_item_selected')", OSD)
    time.sleep(1)
    OSD.click()

    subframe = browser.find_element(By.CSS_SELECTOR, '#frame_subpage')
    browser.switch_to_frame(subframe)
    wait = WebDriverWait(browser,15)
    wait.until(EC.visibility_of_element_located((By.ID, "button_osd_save")))

    checkbox = browser.find_element(By.CSS_SELECTOR,'[for="check_enable_sysinfo"]')
    checkbox.click()
    save_button = browser.find_element(By.CSS_SELECTOR, "#button_osd_save")
    save_button.click()
    browser.switch_to_default_content()

    video = browser.find_element(By.CSS_SELECTOR, "#div_submenu_item_video.cls_submenu_items_text")
    browser.execute_script("arguments[0].setAttribute('class','cls_submenu_items_text cls_submenu_item_selected')", video)
    time.sleep(1)
    video.click()

    subframe = browser.find_element(By.CSS_SELECTOR, '#frame_subpage')
    browser.switch_to_frame(subframe)
    wait = WebDriverWait(browser,15)
    wait.until(EC.visibility_of_element_located((By.ID, "button_video_save")))

    resolution = browser.find_element(By.CSS_SELECTOR, "#select_video_main_resolution")
    resolution.find_element(By.CSS_SELECTOR,'option:nth-child(1)').click()
    time.sleep(1)
    checkbox_main_audio = browser.find_element(By.ID, 'check_enable_main_withaudio')
    checkbox_main_audio.click()

    checkbox_sub_audio = browser.find_element(By.ID, 'check_enable_sub_withaudio')
    checkbox_sub_audio.click()
    save_button = browser.find_element(By.ID, "button_video_save")
    #save_button.click()

    browser.switch_to_default_content()
    return browser

if __name__ == "__main__":
    pppoe_login = 'SAMPLE_LOGIN'
    pppoe_password = 'SAMPLE_PASSWORD'
    admin_pass = "yabdeaps"
    try:
        browser = login(browser(),def_passw)
        browser = go_to_options(browser)
        browser = go_to_time(browser)
        browser = set_time(browser)
        browser = set_new_admin_password_on_security_page(browser, admin_pass)
        browser = go_to_options(browser)
        browser = set_pppoe_login_password(browser, pppoe_login, pppoe_password)
        browser = set_video_options(browser)
    except Exception as error:
        print(f"Трейсбэк: {error}")
    finally:
        time.sleep(5)
        print('\nclosing browser...')
        browser.quit()