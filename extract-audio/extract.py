import pandas as pd
from bs4 import BeautifulSoup
from rich import print
from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import logging
logging.basicConfig(filename='convert.log',level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
print('MyHostedNumbers Audio Extractor', )
pub_date = datetime.today()
start_date = input('Enter the start date (MM-DD-YYYY):').strip()
end_date = input('Enter the end date (MM-DD-YYYY):').strip()

print(start_date,end_date)
start_date = datetime.strptime(start_date,"%m-%d-%Y")
end_date = datetime.strptime(end_date,"%m-%d-%Y")

logging.info(f'Downloading audio files from {start_date} to {end_date}')
# print(start_date)
async def extract_ids(soup):

    table = soup.find('table', attrs={'class': 'style2'})
    inputs = table.find_all('input')
    # print(len(inputs))

    ids = [i.get('id') for i in inputs]
    ids = [i[4:] for i in ids if 'chk' in i]
    df = pd.read_html(str(table))[0]
    time_only= df[df.DATE.str.contains(':')][['FROM',"DATE"]]
    time_only.DATE = time_only.DATE.apply(lambda x: datetime.strptime(str(pub_date.date()) +' '+x,'%Y-%m-%d %I:%M %p' ))
    date_only = df[~df.DATE.str.contains(':')][['FROM',"DATE"]]
    date_only.DATE=date_only['DATE'].apply(lambda x: x + ', {}'.format(datetime.now().year))
    date_only.DATE=date_only['DATE'].apply(lambda x: datetime.strptime(x, '%b %d, %Y'))
    date_time = pd.concat([time_only,date_only])
    a = df.merge(date_time, on='FROM',how='left')
    df['DATE'] = a['DATE_y']
    del a
    del time_only
    del date_only
    df['ids'] = pd.Series(ids, )
    df = df[(df.DATE <= end_date)& (df.DATE >= start_date)]
    print(df.DATE)

    df = df.set_index('DATE')
    df.DURATION = '00:' + df.DURATION
    df.DURATION = (pd.to_timedelta(df.DURATION.str.strip()))

    m = (df['DURATION'].dt.seconds >= 60)
    df = df[m]
    # print(df)
    return df.ids.to_dict()

async def main():
    async with async_playwright() as p:
        logging.info('Started')
        browser = await p.chromium.launch(
        )

        payload = {'username': 'gomedia',
                   'password': 'Shaibi17'}

        page = await browser.new_page()
        await page.goto('https://my.hostednumbers.com/login.aspx')
        await page.fill('input#username', payload['username'])
        await page.fill('input#password', payload['password'])
        await page.click('#ctl00_MainContent_Button1')
        # page.is_visible(page.locator('xpath=//*[@id="ctl00_PageContent_dgServices"]/div/table/tbody/tr/td/div/div/div/div[1]/div/div[2]'))
        await page.wait_for_selector(
            '#ctl00_PageContent_dgServices > div > table > tbody > tr > td > div > div > div > div:nth-child(1) > div > div.RightWrapper.top')
        # page.locator('.ib fs20 pb10').click()
        await page.click(
            '#ctl00_PageContent_dgServices > div > table > tbody > tr > td > div > div > div > div:nth-child(1) > div > div.RightWrapper.top > a.ib.fs20.pb10')
        await page.wait_for_selector('#aspnetForm')
        await page.click(
            '#aspnetForm > div.PageBox > div.PageBottomRow > div.PageContent > div > div.Tabs > ul > li:nth-child(2) > a')
        await page.wait_for_selector('iframe')
        await page.goto("https://my.hostednumbers.com/Mailbox/Messages/List.aspx")
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        ids =  await extract_ids(soup)
        os.makedirs(f'./myhostednumbers-{start_date.date()}-{end_date.date()}', exist_ok=True)
        logging.info(f'Saving mp3 files in "./myhostednumbers-{start_date.date()}-{end_date.date()}"')
        for key, val in ids.items():
            async with page.expect_download() as download_info:
                try:
                    await page.goto(
                        'https://my.hostednumbers.com/Mailbox/Messages/get.aspx?MsgID={}&format=MP3'.format(val))
                except:
                    pass
            download = await download_info.value
            await download.save_as(f'./myhostednumbers-{start_date.date()}-{end_date.date()}'+'/{}-{}.mp3'.format(val, str(key)[:-8]))
        logging.info(f'Successful download')
        print('Successful Download')

if __name__ == '__main__':
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    title=loop.run_until_complete(main())