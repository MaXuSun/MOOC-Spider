"""
本代码由[Tkinter布局助手]生成
当前版本:3.1.2
官网:https://www.pytk.net/tkinter-helper
QQ交流群:788392508
"""
from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askdirectory
from spider import SpiderMOOC
from queue import Queue
import sys
import os
import threading
"""
全局通用函数
"""


class TextPrint(object):
    def __init__(self, text):
        self.text = text
        self.queue = Queue()

    def print(self, string):
        self.queue.put(string+'\n')
        # self.text.insert(END,string+'\n')

    def clear(self):
        self.text.delete(1.0, END)

    def show_msg(self):
        while not self.queue.empty():
            self.text.insert(END, self.queue.get())


class WinGUI(Tk):
    def __init__(self):
        super().__init__()
        self.__win()
        self.tk_label_cookie_path = self.__tk_label_cookie_path()
        self.tk_input_cookie_path = self.__tk_input_cookie_path()
        self.tk_input_course_url = self.__tk_input_course_url()
        self.tk_input_save_dir = self.__tk_input_save_dir()
        self.tk_label_quality = self.__tk_label_quality()
        self.tk_label_workers = self.__tk_label_workers()
        self.tk_select_box_quality = self.__tk_select_box_quality()
        self.tk_select_box_workers = self.__tk_select_box_workers()
        self.tk_text_log = self.__tk_text_log()
        self.tk_label_download = self.__tk_label_download()
        self.tk_select_box_download = self.__tk_select_box_download()
        self.tk_label_course_url = self.__tk_label_course_url()
        self.tk_label_save_dir = self.__tk_label_save_dir()
        self.tk_button_open = self.__tk_button_open()
        self.tk_button_start = self.__tk_button_start()
        self.tk_image_sponsor = self.__tk_image_sponsor()
        self.tk_label_sponsor = self.__tk_label_sponsor()

    def __win(self):
        self.title("MOOC下载助手")
        # 设置窗口大小、居中
        width = 820
        height = 360
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        geometry = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.geometry(geometry)
        self.resizable(width=False, height=False)

    def __tk_label_cookie_path(self):
        label = Label(self, text="cookie路径:", anchor="center")
        label.place(x=10, y=10, width=100, height=25)
        return label

    def __tk_input_cookie_path(self):
        ipt = Entry(self)
        ipt.insert(0, './cookie.txt')
        ipt.place(x=120, y=10, width=300, height=25)

        return ipt

    def __tk_input_course_url(self):
        ipt = Entry(self)
        ipt.place(x=120, y=40, width=300, height=25)
        return ipt

    def __tk_input_save_dir(self):
        ipt = Entry(self)
        ipt.insert(0, './Download')
        ipt.place(x=120, y=70, width=250, height=25)
        return ipt

    def __tk_label_quality(self):
        label = Label(self, text="视频质量：", anchor="center")
        label.place(x=440, y=10, width=65, height=25)
        return label

    def __tk_label_workers(self):
        label = Label(self, text="线程数：", anchor="center")
        label.place(x=440, y=40, width=65, height=25)
        return label

    def __tk_select_box_quality(self):
        cb = Combobox(self, state="readonly")
        cb['values'] = ("0:流畅", "1:标清", "2:高清")
        cb.place(x=520, y=10, width=70, height=24)
        cb.current(0)
        return cb

    def __tk_select_box_workers(self):
        cb = Combobox(self, state="readonly")
        cb['values'] = ("1", "2", "3", "4", "5")
        cb.place(x=520, y=40, width=70, height=25)
        cb.current(2)
        return cb

    def __tk_text_log(self):
        text = Text(self)
        text.place(x=10, y=140, width=576, height=200)
        return text

    def __tk_label_download(self):
        label = Label(self, text="下载内容：", anchor="center")
        label.place(x=440, y=70, width=65, height=25)
        return label

    def __tk_select_box_download(self):
        cb = Combobox(self, state="readonly")
        cb['values'] = ("字幕", "视频", "所有")
        cb.place(x=520, y=70, width=70, height=25)
        cb.current(2)
        return cb

    def __tk_label_course_url(self):
        label = Label(self, text="课程url", anchor="center")
        label.place(x=10, y=40, width=100, height=25)
        return label

    def __tk_label_save_dir(self):
        label = Label(self, text="保存路径", anchor="center")
        label.place(x=10, y=70, width=100, height=25)
        return label

    def __tk_button_open(self):
        def select_path():
            path = askdirectory()
            path = path.replace('\\', '/')
            self.tk_input_save_dir.delete(0, 'end')
            self.tk_input_save_dir.insert(0, path)
        btn = Button(self, text="打开", command=select_path)
        btn.place(x=370, y=70, width=51, height=27)
        return btn

    def __tk_button_start(self):
        btn = Button(self, text="开始下载")
        btn.place(x=10, y=100, width=580, height=30)
        return btn


    def __tk_image_sponsor(self):
        root = os.path.join("./middle.gif")
        img = PhotoImage(file=root)
        label = Label(self, image=img)
        label.image = img
        label.place(x=600, y=140, width=200, height=200)
        return label

    def __tk_label_sponsor(self):
        style = Style()
        style.configure('A1.TLabel', font=('微软雅黑', 15), foreground='red')
        label = Label(self, text='   欢迎赞助\n一杯奶茶钱~', anchor='center', style='A1.TLabel')
        label.place(x=640, y=10, width=120, height=120)
        return label


class Win(WinGUI):
    def __init__(self):
        super().__init__()
        self.__event_bind()

        self.info = {
            'cookie_path': None,
            'course_url': None,
            'save_dir': None,
            'quality': 0,
            'workers': 3,
            'download_type': 2,
        }
        self.textprint = TextPrint(self.tk_text_log)
        self.spider = SpiderMOOC(None, None, self.textprint)
        self.after(200, self.show_msg)

    def show_msg(self):
        self.textprint.show_msg()
        self.after(200, self.show_msg)

    def check_params(self):
        errors = []
        if not(self.info['cookie_path'] and os.path.exists(self.info['cookie_path'])):
            errors.append('cookie路径有问题,请输入正确cookie路径.\n')
        if not (self.info['course_url'] and self.info['course_url'].find('tid') > 0):
            errors.append('课程url有问题,请输入正确课程url.\n')
        if not(self.info['save_dir'] and os.path.exists(self.info['save_dir'])):
            errors.append('保存路径有问题,请输入正确保存路径.\n')

        return errors

    def download(self, event):
        def tmp():
            self.spider.cookie_path = self.info['cookie_path']
            self.spider.course_main_url = self.info['course_url']
            self.spider.save_dir = self.info['save_dir']
            self.spider.video_quality = self.info['quality']

            self.spider.start(self.info['download_type'])
            self.spider.close()

        self.info['cookie_path'] = self.tk_input_cookie_path.get()
        self.info['course_url'] = self.tk_input_course_url.get()
        self.info['save_dir'] = self.tk_input_save_dir.get()
        self.info['quality'] = int(self.tk_select_box_quality.get().split(':')[0])
        self.info['workers'] = int(self.tk_select_box_workers.get())
        self.info['download_type'] = self.tk_select_box_download.get()
        self.tk_text_log.delete(1.0, END)
        errors = self.check_params()
        if len(errors) > 0:
            for error in errors:
                self.tk_text_log.insert(END, error)
        else:
            self.start_thread = threading.Thread(target=tmp)
            self.start_thread.start()

    def __event_bind(self):
        self.tk_button_start.bind('<Button-1>', self.download)


if __name__ == "__main__":
    win = Win()

    win.mainloop()
