#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
本软件为自己工作之余学习python所做，主要是想学习PyQt5的使用及了解网络编程。
本人水平较低，难免有不足与错误之处，还望各位大佬指正，也希望自己在此过程中能扩展自己的知识面，提升自己的编程水平
目前软件编写比较笨，存在很大优化空间
"""

# Note:本软件使用 和风天气 提供的天气预报API，需要注册以获取key， 地址 https://dev.heweather.com/
# date:       2019/07/19
# dev os/ver: windows7-64bit, python3.7
# author:     gorkon
# soft ver:   V0.0.1
# change log: 创建程序
# V0.0.2 添加用户输入城市名称选项
# V0.0.3 天气API使用auto_ip选项
# V0.0.5 添加最小化至系统托盘功能，添加后台时自动提示当前天气和明天天气有雨情况
# V0.1.0 添加手动输入城市的功能
# V0.1.2 修复手动模式下，多次输入城市信息时，由于list未清空导致的城市信息不能更新


from weather_ui import Ui_Class
import sys
import time
from PyQt5.QtWidgets import QWidget, QLabel, QApplication
from PyQt5.QtCore import *
import requests

TIMER_CYCLE = 300# 天气信息刷新频率，单位：秒
MY_WEATHER_KEY = r"80aa4504b70a4de4bf27bf4c521dc362"    # 本软件使用的天气API  key
URL_NOW_WEATHER = r"https://free-api.heweather.net/s6/weather/now?location=auto_ip&key="+MY_WEATHER_KEY # 实时天气
URL_FOR_WEATHER = r"https://free-api.heweather.net/s6/weather/forecast?location=auto_ip&key="+MY_WEATHER_KEY  #预测天气

URL_NOW_WEATHER_CID = r"https://free-api.heweather.net/s6/weather/now?location="
URL_FOR_WEATHER_CID = r"https://free-api.heweather.net/s6/weather/forecast?location="
URL_TAIL_CID = r"&key="+MY_WEATHER_KEY

g_cid = ""

#获取天气信息线程
class Update_Thread(QThread):

    #自定义信号
    wt_up_now_sig = pyqtSignal(str, str, str, int)  #分别为城市名、天气、时间、是否坏天气
    wt_up_oth_sig = pyqtSignal(int, str, str, int)  #分别为明天(1)或后天(2)、天气、时间、是否坏天气
    tray_message_sig = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.working = True
        self.isManuMode = False #当前是否是 手动模式,False表示自动
        self.url_now=URL_NOW_WEATHER
        self.url_forecast=URL_FOR_WEATHER
        self.bad_wea=["小雨","中雨","大雨","阵雨","雷阵雨","暴雨","大暴雨","特大暴雨","小到中雨","中到大雨","大到暴雨","暴雨到大暴雨","雨"]
    
        
    #判断 获取的天气信息是否有雨
    # todo 实现太笨，待优化，考虑正则表达式
    def __is_bad_weather(self, wae_str):
        if wae_str in self.bad_wea:
            return 1
        else:
            return 0
            
    #线程执行任务       
    def run(self):
        if self.isManuMode==False:
            self.url_now      = URL_NOW_WEATHER
            self.url_forecast = URL_FOR_WEATHER
        else:
            global g_cid
            self.url_now = URL_NOW_WEATHER_CID + g_cid + URL_TAIL_CID
            self.url_forecast = URL_FOR_WEATHER_CID + g_cid + URL_TAIL_CID
                
        while self.working == True:
            try:
                self.try_msg_str=""
                #获取天气数据，和风天气API使用天气类型now
                rs_we = requests.get(self.url_now).json()
                #分别获取 城市名称、当前时间、天气信息 信息
                city_name = rs_we["HeWeather6"][0]["basic"]["admin_area"] + " - " + rs_we["HeWeather6"][0]["basic"]["parent_city"] + " - " +rs_we["HeWeather6"][0]["basic"]["location"]
                time_info = rs_we["HeWeather6"][0]["update"]["loc"]
                wea_info_str = rs_we["HeWeather6"][0]["now"]["cond_txt"]
                weat_info = (wea_info_str + "  " + rs_we["HeWeather6"][0]["now"]["tmp"] + "度  "+
                            rs_we["HeWeather6"][0]["now"]["wind_dir"] + "  " + rs_we["HeWeather6"][0]["now"]["wind_sc"] + "级")
                detag = self.__is_bad_weather(wea_info_str)
                #如果是有雨天气
                if detag == 1:
                    #触发信号
                    self.wt_up_now_sig.emit(city_name, weat_info, time_info, 1)
                    self.try_msg_str = "当前天气" + " :  " + wea_info_str
                else:
                    self.wt_up_now_sig.emit(city_name, weat_info, time_info, 0)
                
                #获取天气信息，和风天气使用关键字 forecast
                rs_we = requests.get(self.url_forecast).json()
                #获取返回数据中的 明天 的天气信息
                time_info = rs_we["HeWeather6"][0]["daily_forecast"][1]["date"]
                wea_info_str = rs_we["HeWeather6"][0]["daily_forecast"][1]["cond_txt_d"]
                weat_info = (wea_info_str + "  " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][1]["tmp_min"] + " ~ " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][1]["tmp_max"] + "度  " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][1]["wind_dir"] + " " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][1]["wind_sc"] + "级")
                detag = self.__is_bad_weather(wea_info_str)
                if detag == 1:
                    self.wt_up_oth_sig.emit(1, weat_info, time_info, 1)
                    #气泡提示只提示今天和明天两天的信息
                    if len(self.try_msg_str)>5:    #这里的判断是为了气泡提示信息排版整齐
                        self.try_msg_str = self.try_msg_str + "\n" + time_info + " :  " + wea_info_str
                    else:
                        self.try_msg_str = time_info + " :  " + wea_info_str
                else:
                    self.wt_up_oth_sig.emit(1, weat_info, time_info, 0)
                    
                #获取返回数据中的 后天 的天气信息
                time_info = rs_we["HeWeather6"][0]["daily_forecast"][2]["date"]
                wea_info_str = rs_we["HeWeather6"][0]["daily_forecast"][2]["cond_txt_d"]
                weat_info = (wea_info_str + "  " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][2]["tmp_min"] + " ~ " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][2]["tmp_max"] + "度  " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][2]["wind_dir"] + " " + 
                            rs_we["HeWeather6"][0]["daily_forecast"][2]["wind_sc"] + "级")
                detag = self.__is_bad_weather(wea_info_str)
                if detag == 1:
                    self.wt_up_oth_sig.emit(2, weat_info, time_info, 1)
                else:
                    self.wt_up_oth_sig.emit(2, weat_info, time_info, 0)
                
                #触发托盘气泡信号
                self.tray_message_sig.emit(self.try_msg_str)
                time.sleep(TIMER_CYCLE)  #线程sleep
            except Exception as e:
                pass
    
#主类
class Weather_Class(QObject):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Class()
        self.up_thread = Update_Thread()
    
    #更新 当前天气 信息
    def up_now_wea(self, str_city, str_wea, str_time, bad_tag):
        self.ui.update_location(str_city)
        if bad_tag==1:
            self.ui.set_now_weathercolor("red")#坏天气就用红色字体显示
        else:
            self.ui.set_now_weathercolor("blue")
        self.ui.update_now_weather(str_wea)
        self.ui.update_time(str_time)
    
    #更新 明天或后天 天气信息
    def up_otr_wea(self, index, str_wea, str_time, bad_tag):
        if index==1:    # 明天
            self.ui.set_label(1, str_time)
            if bad_tag==1:
                self.ui.set_otr_weathercolor(1, "red")
            else:
                self.ui.set_otr_weathercolor(1, "blue")
            self.ui.update_1_weather(str_wea)
        else:
            self.ui.set_label(2, str_time)
            if bad_tag==1:
                self.ui.set_otr_weathercolor(2, "red")
            else:
                self.ui.set_otr_weathercolor(2, "blue")
            self.ui.update_2_weather(str_wea)
        
    #主UI上 确定 按钮的响应函数
    def slot_btn(self, isManu):
        if isManu==False: #自动模式
            self.up_thread.isManuMode = False
        else:
            self.up_thread.isManuMode = True
            global g_cid
            g_cid = self.ui.get_cid()
        time.sleep(0.5)
        self.up_thread.start()
            
    #将自定义信号和槽函数关联，并启动获取天气信息的线程
    def update_wea_ui(self):
        self.up_thread.wt_up_now_sig.connect(self.up_now_wea)
        self.up_thread.wt_up_oth_sig.connect(self.up_otr_wea)
        self.up_thread.tray_message_sig.connect(self.ui.tray_msg_show)
        self.ui.click_btn_sig.connect(self.slot_btn)


#程序主入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    wea = Weather_Class()
    wea.update_wea_ui()
    sys.exit(app.exec_())
    