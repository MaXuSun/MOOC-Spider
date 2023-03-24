import requests
import os
import json
import shutil
from urllib.parse import urlparse, parse_qs
from glob import glob
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait

# 获得所有视屏的信息包括bizId
all_chapter_url = "https://www.icourse163.org/web/j/courseBean.getLastLearnedMocTermDto.rpc?csrfKey={csrfKey}"
# 可以获得章节的视屏的videoId和signature
chapter_info_url = 'https://www.icourse163.org/web/j/resourceRpcBean.getResourceToken.rpc?csrfKey={csrfKey}'
# 可以获得章节视屏的详细内容：不同分辨率的视屏以及字幕文件
chapter_content_url = 'https://vod.study.163.com/eds/api/v1/vod/video?videoId={videoId}&signature={signature}&clientType=1'


def save_to_json(data):
    with open('tmp.json', 'w') as f:
        f.write(json.dumps(data))


class Lesson:
    def __init__(self, chapter_name, id, name, videoId, signature, video_urls, srt_urls, m3u8s):
        self.chapter_name = chapter_name
        self.id = id
        self.name = name
        self.videoId = videoId
        self.signature = signature
        self.video_urls = video_urls
        self.srt_urls = srt_urls
        self.m3u8s = m3u8s

    def __str__(self):
        return "id={};name={};signature={};video_urls={};srt_urls={}".format(self.id, self.name, self.videoId, self.signature, self.video_urls, self.srt_urls)

    def get_m3u8_urls(self, quality=0):
        index = self.video_urls[quality].rfind('/')
        video_url = self.video_urls[quality][:index+1]
        m3u8_text = self.m3u8s[quality].split('\n')
        m3u8_urls = []
        for line in m3u8_text:
            line = line.strip()
            if line.endswith('ts'):
                m3u8_urls.append(video_url+line)
        return m3u8_urls

    def save_to_json(self, file):
        if not ''.endswith('json'):
            file = file+'.json'
        with open(file, 'w') as f:
            f.write(json.dumps(self.__dict__))

    @staticmethod
    def load_from_json(file):
        assert file.endswith('json')
        lesson = Lesson(None, None, None, None, None, None, None, None)
        with open(file, 'r') as f:
            content = json.loads(f.read())
        for k, v in content.items():
            lesson.__setattr__(k, v)
        return lesson


class SpiderMOOC:
    def __init__(self, cookie_path, course_main_url, textprint=None, video_quality=0, save_dir='./Spark', workers=3) -> None:
        self.cookie_path = cookie_path
        self.course_main_url = course_main_url
        self.video_quality = video_quality
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.workers = workers
        self.session = requests.Session()
        self.textpint = textprint

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Safari/537.36'
        }
        self.lessons = None

    def get_cookie(self, cookie):
        if len(cookie) < 250:
            with open(cookie, 'r') as f:
                cookie = f.readline().strip()
        return dict([l.split("=", 1) for l in cookie.split("; ")])

    def print(self, string):
        if self.textpint:
            self.textpint.print(string)
        else:
            print(string)

    def __get_video_id_signature__(self, bizId):
        data = {
            'bizId': bizId,
            'bizType': 1,
            'contentType': 1
        }
        r = self.session.post(self.chapter_info_url, data=data,
                              headers=self.headers, cookies=self.cookie)
        result = r.json()['result']['videoSignDto']
        return result['signature'], result['videoId']

    def __get_srt_video_url__(self, videoId, signature):
        data = {
            'videoId': videoId,
            'signature': signature,
            'clientType': 1
        }
        url = self.chapter_content_url.format(
            videoId=videoId, signature=signature)
        r = self.session.get(
            url, data=data, headers=self.headers, cookies=self.cookie)
        result = r.json()['result']
        srt_urls = [srt['url'] for srt in result['srtCaptions']]
        video_urls = [video['videoUrl'] for video in result['videos']]
        return video_urls, srt_urls

    def __get_video_m3u8s__(self, url):
        r = self.session.get(url, headers=self.headers, cookies=self.cookie)
        return r.text

    def __spider_one_lesson_srt__(self, lesson, quality=0):
        if len(lesson.srt_urls) <= quality:
            self.print('课程：{}，没有字幕'.format(lesson.name))
            return False
        url = lesson.srt_urls[quality]
        r = self.session.get(url)
        save_dir = os.path.join(self.save_dir, 'video_srt',
                                lesson.chapter_name, lesson.name)
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, lesson.name+'.srt'), 'w', encoding='utf-8') as f:
            content = r.text.split('\n')
            f.write(''.join(content))
        self.print('课程：{}，字幕爬取完成'.format(lesson.name))

    def __spider_one_lesson_video__(self, lesson, quality=0):
        save_dir = os.path.join(self.save_dir, 'video_srt', lesson.chapter_name, lesson.name)
        tmp_dir = os.path.join(save_dir, 'temp')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(tmp_dir, exist_ok=True)

        if quality >= len(lesson.get_m3u8_urls()):
            quality = len(lesson.get_m3u8_urls())-1
            self.print('课程:{},的视频质量最多大为{}，这里降为{}'.format(lesson.name, quality, quality))
        left_m3u8_urls = lesson.get_m3u8_urls(quality)

        def spider_one_m3u8(url, save_path):
            with open(save_path, 'wb') as f:
                content = self.session.get(url, headers=self.headers).content
                f.write(content)
            return True, os.path.basename(save_path)

        # 多线程爬ts
        success_m3u8_names = []
        with ThreadPoolExecutor(max_workers=self.workers*3) as t:
            thread_lists = []
            for m3u8_url in left_m3u8_urls:
                index = m3u8_url.rfind('/')
                name = m3u8_url[index+1:]
                save_path = os.path.join(tmp_dir, name)
                thread_lists.append(t.submit(lambda p: spider_one_m3u8(*p), [m3u8_url, save_path]))

            for feature in as_completed(thread_lists):
                succ, name = feature.result()
                if succ:
                    success_m3u8_names.append(name)
            wait(thread_lists, timeout=60.0*10)

        # 合并爬取的ts短视频
        success_m3u8_names.sort()
        with open(os.path.join(save_dir, lesson.name+'.ts'), 'ab+') as f:
            for name in success_m3u8_names:
                with open(os.path.join(tmp_dir, name), 'rb') as rf:
                    content = rf.read()
                f.write(content)
        shutil.rmtree(tmp_dir)
        self.print('课程:{}；爬取完毕，成功率:{}%'.format(lesson.name, 100*len(success_m3u8_names)/len(left_m3u8_urls)))

    def load_all_lessons_info(self, lesson_root_dir):
        lessons = []
        for path in glob(os.path.join(lesson_root_dir, 'lesson_info', '*', '*.json')):
            lessons.append(Lesson.load_from_json(path))
        self.lessons = lessons
        return lessons

    def get_all_lessons_info(self):

        def spider_one_lesson_info(id, name, chapter_name):
            """爬取一个课程的信息"""
            signature, videoId = self.__get_video_id_signature__(id)
            video_url, srt_url = self.__get_srt_video_url__(videoId, signature)
            m3u8 = [self.__get_video_m3u8s__(vu) for vu in video_url]
            return Lesson(chapter_name, id, name, videoId, signature, video_url, srt_url, m3u8)

        def spider_one_chapter_info(chapter):
            """调用spider_one_lesson_info爬取一章课程的信息"""
            lessons = []
            ids = [unit['id'] for lesson in chapter['lessons'] for unit in lesson['units']]
            names = [unit['name'] for lesson in chapter['lessons'] for unit in lesson['units']]
            chapter_names = [chapter['name']]*len(names)
            with ThreadPoolExecutor(max_workers=self.workers) as t:
                obj_list = []
                for args in zip(ids, names, chapter_names):
                    obj = t.submit(lambda p: spider_one_lesson_info(*p), args)
                    obj_list.append(obj)

                for feture in as_completed(obj_list):
                    lesson = feture.result()
                    lessons.append(lesson)
            return lessons

        data = {
            'termId': self.tid
        }

        r = self.session.post(self.all_chapter_url, data=data,
                              cookies=self.cookie, headers=self.headers)
        result = r.json()['result']
        lessons = []

        chapters = [chapter for chapter in result['mocTermDto']['chapters']
                    if 'lessons' in chapter and chapter['lessons'] is not None]
        with ThreadPoolExecutor(max_workers=self.workers) as pt:
            pobj_list = []
            for chapter in chapters:
                pobj_list.append(pt.submit(spider_one_chapter_info, chapter))
            for feature in as_completed(pobj_list):
                chap_lessons = feature.result()
                lessons.extend(chap_lessons)

        self.lessons = lessons
        return lessons

    def spider_lessons_srt(self):
        """
        根据爬取的信息多线程爬字幕
        :return:
        """
        if not self.lessons:
            self.lessons = self.get_all_lessons_info()

        with ThreadPoolExecutor(max_workers=self.workers) as t:
            for lesson in self.lessons:
                t.submit(self.__spider_one_lesson_srt__, lesson)

    def spider_lessons_video(self):
        """根据爬取的信息多线程爬视频"""
        if not self.lessons:
            self.lessons = self.get_all_lessons_info()

        with ThreadPoolExecutor(max_workers=self.workers) as t:
            for lesson in self.lessons:
                t.submit(lambda p: self.__spider_one_lesson_video__(*p), (lesson, self.video_quality))

    def save_lessons_infos(self):
        for lesson in self.lessons:
            os.makedirs(os.path.join(self.save_dir, 'lesson_info', lesson.chapter_name), exist_ok=True)
            lesson.save_to_json(os.path.join(self.save_dir, 'lesson_info', lesson.chapter_name, lesson.name))

    def close(self):
        self.session.close()

    def start(self, download_type):
        self.cookie = self.get_cookie(self.cookie_path)
        self.tid = parse_qs(urlparse(self.course_main_url).query)['tid'][0]
        self.csrfKey = self.cookie['NTESSTUDYSI']

        self.all_chapter_url = all_chapter_url.format(csrfKey=self.csrfKey)
        self.chapter_info_url = chapter_info_url.format(csrfKey=self.csrfKey)
        self.chapter_content_url = chapter_content_url

        self.get_all_lessons_info()
        self.save_lessons_infos()
        if download_type in ['所有', '字幕']:
            self.spider_lessons_srt()
        if download_type in ['所有', '视频']:
            self.spider_lessons_video()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='命令行中传入一个数字')
    parser.add_argument('--save-dir', type=str, help='爬取的文件，保存的路径')
    parser.add_argument('--quality', type=int, default=0, help='爬取视频的质量')
    parser.add_argument('--cookie-path', type=str, default='./cookie.txt', help='存放cookie的路径')
    parser.add_argument('--course-url', type=str, help='课程的url', default='https://www.icourse163.org/learn/XMU-1205811805?tid=1466865454')
    parser.add_argument('--workers', type=int, default=3, help='线程数')
    args = parser.parse_args()

    spider = SpiderMOOC(args.cookie_path, args.course_url,
                        save_dir=args.save_dir,
                        workers=args.workers)

    spider.start('字幕')
    spider.close()
