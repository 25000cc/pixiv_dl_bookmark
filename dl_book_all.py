# -*- coding:utf-8 -*- 3.5.7

from pixivpy3 import *
import json
import time
import random
from time import sleep
import shutil
import sys, io, re, os, glob
from pprint import pprint
import pandas as pd
import numpy as np
from PIL import Image
from tqdm import tqdm

class PixivCrawler(object):

    def __init__(self, api, illust_db='pixiv_illusts.db'):
        self.api = api
        self.illust_db = illust_db
        self.user_info = None

    def randSleep(self, base=0.1, rand=0.5):
        time.sleep(base + rand*random.random())

    def GetUserDetail(self, user_id):
        self.last_user = self.api.user_detail(user_id)
        return self.last_user

    def GetUserBookmarks(self, user_id, restrict='public'):
        df_list = []
        next_qs = {'user_id': user_id, 'restrict': restrict}

        user = self.GetUserDetail(user_id)
        self.randSleep(0.1)

        with tqdm(total=user.profile.total_illust_bookmarks_public,
                  desc="api.user_bookmarks_illust") as pbar:
            while next_qs != None:
                json_result = self.api.user_bookmarks_illust(**next_qs)
                tmp_df = pd.DataFrame.from_dict(json_result.illusts)
                df_list.append(tmp_df)
                pbar.update(tmp_df.shape[0])
                next_qs = self.api.parse_qs(json_result.next_url)
                self.randSleep(0.1)

        df = pd.concat(df_list)
        return df.reset_index(drop=True)

    def download(self, url):
        name = url.split('/')[-1]
        self.api.download(url, name='images/{}'.format(name))

    def dl_ugoira(self, illust_id):
        path = 'images/{}.gif'.format(illust_id)
        if not os.path.exists(path):
            illust = self.api.illust_detail(illust_id)
            ugoira_url = illust.illust.meta_single_page.original_image_url.rsplit('0', 1)
            ugoira = self.api.ugoira_metadata(illust_id)
            ugoira_frames = len(ugoira.ugoira_metadata.frames)
            ugoira_delay = ugoira.ugoira_metadata.frames[0].delay
            dir_name = str(illust_id)+'_ugoira'

            if not os.path.isdir(dir_name):
                os.mkdir(dir_name)
            
            for frame in range(ugoira_frames):
                frame_url = ugoira_url[0] + str(frame) + ugoira_url[1]
                self.api.download(frame_url, path=dir_name)
            
            frames = glob.glob(f'{dir_name}/*')
            frames.sort(key=os.path.getmtime, reverse=False)
            ims = []
            for frame in frames:
                ims.append(Image.open(frame))
            ims[0].save(f'images/{illust_id}.gif', save_all=True, append_images=ims[1:],
                optimize=False, duration=ugoira_delay, loop=0)
            shutil.rmtree(f'{dir_name}/')

    def dl_book_all(self, user_id):
        df = self.GetUserBookmarks(user_id)[0]
        for i in tqdm(iterable=range(len(df)), desc='download all bookmark'):
            type_ = df[i]['type']
            page_count = df[i]['page_count']
            meta_single_page = df[i]['meta_single_page']
            meta_pages = df[i]['meta_pages']
            if page_count != 1:
                # manga
                for j in range(page_count):
                    self.download(meta_pages[j].image_urls.original)
            else:
                if type_ == 'ugoira':
                    # ugoira
                    illust_id = meta_single_page.original_image_url.split('/')[-1][:8]
                    self.dl_ugoira(illust_id)
                else:
                    # single illust
                    self.download(meta_single_page.original_image_url)


def main():
    # get client info
    f = open("client.json", "r")
    client_info = json.load(f)
    f.close()
    pixiv_id = client_info["pixiv_id"]
    password = client_info["password"]
    user_id = client_info["user_id"]

    # login to pixiv
    api = AppPixivAPI()
    api.login(pixiv_id, password)

    # make directory to save images
    dir_name = 'images'
    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)

    # download all bookmarks
    crawl = PixivCrawler(api)
    crawl.dl_book_all(user_id)

if __name__ == '__main__':
    main()