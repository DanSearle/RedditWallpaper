#!/usr/bin/env python

import logging
log = logging.getLogger(__name__)

import argparse

import os
import sys
import traceback
import shutil

import mimetypes
import itertools
import urllib

import praw
from PIL import Image


def parse_command_line(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('output_dir', metavar='dir', type=str, nargs=1,
                        help='Directory to write the wallpapers to')
    parser.add_argument("-v", "--verbose", dest="verbose_count",
                        action="count", default=0,
                        help="increases log verbosity for each occurence.")
    parser.add_argument("-W", "--min-width", dest='min_width', type=int,
                        default=1920,
                        help="Minimum width of image to accept.")
    parser.add_argument("-H", "--min-height", dest='min_height', type=int,
                        default=1080,
                        help="Minimum height of image to accept.")
    parser.add_argument("-t", "--time", dest='time', type=str,
                        default='',
                        help="Time to list top images from. Can be one of [hour, day, week, month, year], do not set for all")
    parser.add_argument("-r", "--random", dest='random', action='store_true',
                        help="Set to use a random item rather than using the top from the subreddits. Not compatiable with time. (May be slower due to randomisation and matching min height/width)")
    parser.add_argument("-s", "--screens", dest='screens', type=int,
                        default=3,
                        help="Number of screens to read images for")
    parser.add_argument('subreddit', nargs='+')
    arguments = parser.parse_args(argv[1:])
    logging.basicConfig(level=max(3 - arguments.verbose_count, 0) * 10)
    return arguments


def get_urls(sub, min_size):
    for post in sub:
        log.info('Loading from url {0}'.format(post.url))
        link_type = mimetypes.guess_type(post.url)[0]
        log.debug('URL {0} type {1}'.format(post.url, link_type))
        if link_type and link_type.startswith('image/'):
            ret = urllib.urlretrieve(post.url)
            filename = ret[0]
            try:
                im = Image.open(filename)
                if im.size >= min_size:
                    log.info("Image is big enough @ {0}".format(im.size))
                    yield post.url, filename
            except IOError:
                log.debug("Cannot load image from {0.url}: {1}".format(post, traceback.format_exc()))
            finally:
                if os.path.exists(filename):
                    os.remove(filename)


def main():
    arguments = parse_command_line(sys.argv)
    wallpapers = arguments.output_dir[0]
    if not os.path.isdir(wallpapers):
        os.mkdir(wallpapers)

    params = {}
    if arguments.time:
        params = {'t': arguments.time}

    api = praw.Reddit(user_agent='python')
    reddits = '+'.join(arguments.subreddit)
    log.info("Using subreddits {0}".format(reddits))
    sub = api.get_subreddit(reddits)
    generator = sub.get_top(params=params)
    if arguments.random:
        log.info("Using random generator")
        generator = random_generator(api, sub, params=params)

    urls = get_urls(generator, (arguments.min_width, arguments.min_height))
    for n, (url, filename) in enumerate(itertools.islice(urls, 0, arguments.screens)):
        log.info("Using image from url {0} for screen {1} filename {2}".format(url, n, filename))
        #urllib.urlretrieve(url, os.path.join(wallpapers, "reddit-{0}".format(n)))
        newfile = os.path.join(wallpapers, "reddit-{0}".format(n))
        log.debug("Copying from {0} to {1}".format(filename, newfile))
        shutil.copyfile(filename, newfile)
    log.info("Running nitrogen --restore")
    os.system("nitrogen --restore >/dev/null 2>&1")
    log.info("Ran nitrogen --restore")

def random_generator(api, sub, params):
    def gen():
        import random
        while True:
            try:
                yield getitems(api, str(sub), unique=random.randint(0, 99999))
            except (GeneratorExit, StopIteration):
                raise
            except:
                log.debug("Cannot load random submission trying again {0}".format(traceback.format_exc()))
    return gen()

def getitems(api, subreddit, unique=0):
    """Return list of items from a subreddit."""
    url = 'http://www.reddit.com/r/%s/random/.json?unqiue=%i' % (subreddit, unique)
    try:
        api._request(url, raw_response=True)
    except praw.errors.RedirectException as exc:
        return api.get_submission(exc.response_url)
    raise praw.errors.ClientException('Expected exception not raised.')

if __name__ == "__main__":
    main()
