import asyncio
import csv
import math
import os
import shutil
from datetime import datetime

import aiohttp
from PIL import Image
from fpdf import FPDF


class Main():
    def __init__(self):
        cameras = self.read_camera_list('cameras.csv')
        now = datetime.utcnow()
        now = datetime.fromtimestamp(math.floor(now.timestamp()))
        cache = self.create_cache()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.load_images(loop, cameras, cache))
        self.generate_book(now, cameras)
        self.clear_cache(cache)

    def create_cache(self):
        cache = '{}/cache'.format(os.getcwd())
        self.clear_cache(cache)
        os.mkdir(cache)
        return cache

    def read_camera_list(self, csv_path_):
        cameras = []
        with open(csv_path_, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',', quotechar='"')
            for row in reader:
                if row.__len__() == 4:
                    camera = Camera(row[0], row[1], row[2], row[3])
                    cameras.append(camera)
        cameras.sort(key=lambda c: c.latitude, reverse=True)
        return cameras

    async def load_images(self, loop_, cameras_, directory_):
        print('Loading images ...')
        tasks = []
        for c in cameras_:
            c.file = '{}/{}.jpg'.format(directory_, len(tasks))
            task = asyncio.ensure_future(self.load_image(c))
            tasks.append(task)
        for c, b in await asyncio.gather(*tasks):
            with open(c.file, 'wb') as handle:
                handle.write(b)

    async def load_image(self, camera_):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(camera_.url) as response:
                    bytes = await response.read()
                    print('... {}'.format(camera_.location))
                    return camera_, bytes
        except (aiohttp.errors.ClientResponseError,
                aiohttp.errors.ClientRequestError,
                aiohttp.errors.ClientOSError,
                aiohttp.errors.ClientDisconnectedError,
                aiohttp.errors.ClientTimeoutError,
                asyncio.TimeoutError,
                aiohttp.errors.HttpProcessingError,
                ValueError) as exc:
            print('Error loading image from {} - {}'.format(camera_.location, camera_.url))
            exit()
        return None

    def generate_book(self, now_, cameras_):
        page_width = 260
        page_height = 200
        text_large = 15
        text_regular = 11
        title = 'now'
        edition = '{} UTC'.format(now_)
        pdf = FPDF('P', 'mm', (page_width, page_height))
        pdf.set_author('Birk Weiberg')
        pdf.set_title('{} = {}'.format(title, edition))
        pdf.set_margins(0, 0, 0)
        pdf.add_page()
        pdf.set_font('Arial', 'B', text_large)
        pdf.cell(0, 0.5 * page_height, '', 0, 1, 'C')
        pdf.cell(0, 0, title, 0, 0, 'C')
        pdf.add_page()
        pdf.add_page()
        pdf.cell(0, 0.5 * page_height, '', 0, 1, 'C')
        pdf.cell(0, 0, edition, 0, 0, 'C')
        pdf.add_page()
        pdf.set_font('Arial', '', text_regular)
        pdf.cell(0, 0.8 * page_height, '', 0, 1, 'C')
        pdf.cell(0, 0.5 * text_regular, 'Birk Weiberg, 2016', 0, 1, 'C')
        pdf.cell(0, 0.5 * text_regular, 'https://github.com/birk/now-book', 0, 1, 'C')
        pdf.add_page()
        for c in cameras_:
            pdf.add_page()
            pdf.add_page()
            try:
                w, h = self.get_prop_size(c.file, 0.7 * page_width, 0.6 * page_height)
            except (OSError) as exc:
                print('Error loading image from {} - {}'.format(c.location, c.url))
                return
            pdf.image(c.file, 0.5 * (page_width - w), 0.4 * (page_height - h), w, h)
            pdf.cell(0, 0.85 * page_height, '', 0, 1, 'C')
            pdf.cell(0, 0.5 * text_regular, c.location_str, 0, 1, 'C')
            pdf.link(0.4 * page_width, 0.84 * page_height, 0.2 * page_width, 0.04 * page_height, c.link)
        pdf.add_page()
        pdf.add_page()
        while pdf.page % 4 != 0:
            pdf.add_page()
        file_name = '{}-{}.pdf'.format(title, str(now_).replace(' ', '-').replace(':', '-'))
        pdf.output(file_name, 'F')
        print('now-book: {}'.format(file_name))

    def get_prop_size(self, path_, max_width_, max_height_):
        img = Image.open(path_)
        img_w, img_h = img.size
        max_prop = max_width_ / max_height_
        img_prop = img_w / img_h
        if img_prop > max_prop:
            # wide image
            w = max_width_
            h = img_h * max_width_ / img_w
        else:
            # high image
            h = max_height_
            w = img_w * max_height_ / img_h
        return w, h

    def clear_cache(self, cache_path_):
        if os.path.isdir(cache_path_):
            shutil.rmtree(cache_path_)


class Camera():
    def __init__(self, location_, longitude_, latitude_, url_):
        self.location = location_
        self.longitude = float(longitude_)
        self.latitude = float(latitude_)
        self.url = url_
        self.file = None

    @property
    def location_str(self):
        return '{} / {}'.format(self.longitude, self.latitude)

    @property
    def link(self):
        return 'https://www.google.com/maps/place/{}+{}'.format(self.longitude, self.latitude)


if __name__ == '__main__':
    m = Main()
