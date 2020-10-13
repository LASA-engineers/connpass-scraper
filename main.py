import re
import time

from bs4 import BeautifulSoup
import requests


MEMBER_BASE = "https://laboratoryautomation.connpass.com/participation/"
EVENT_BASE = "https://laboratoryautomation.connpass.com/event/"


class Member(object):
    @classmethod
    def load_from_html(cls, html):
        link = html.find("p", class_="GroupMemberDisplayName").a
        name = link.string
        idstr = re.compile(r"^.*/([^/]+)/$").search(link["href"]).group(1)
        count = re.compile(r"^(\d+) 回$").search(html.find("td", class_="event").string).group(1)
        date = parse_date(html.find("td", class_="date").string)
        join = parse_date(html.find("td", class_="join_date").string)
        return Member(name, idstr, count, date, join)

    def __init__(self, name, idstr, count, date, join):
        self.name = name
        self.idstr = idstr
        self.count = count
        self.date = date
        self.join = join
        self.attend = {}

    def __str__(self):
        return f"Member({self.idstr}, {self.name}, {self.join}, {self.count}, {self.date})"


class Event(object):
    @classmethod
    def load_from_html(cls, html):
        date = parse_date(list(html.find("p", class_="schedule").stripped_strings)[-1])
        link = html.find("p", class_="event_title").a
        title = link.string
        url = link["href"]
        return Event(date, title, url)

    def __init__(self, date, title, url):
        self.date = date
        self.title = title
        self.url = url

    def __str__(self):
        return f"Event({self.date}, {self.title})"


def parse_date(s):
    if not s:
        return s
    return re.compile(r"^(\d{4}/\d{2}/\d{2}).*$").search(s).group(1)


def get_page(url):
    print(f"GET {url}")
    res = requests.get(url)
    time.sleep(3)
    return BeautifulSoup(res.content, "html.parser")


def visit_next(base, soup):
    next_candidate = soup.find("div", class_="paging_area").ul.find_all("li")[-1].find("a")
    if next_candidate is None:
        return None
    else:
        return get_page(base + next_candidate["href"])


def get_group_members():
    members = []

    page = get_page(MEMBER_BASE)
    while True:
        for member in page.find_all("tr", class_="GroupMemberProfile"):
            members.append(Member.load_from_html(member))

        page = visit_next(MEMBER_BASE, page)
        if not page:
            break

    return members


def get_group_events():
    events = []

    page = get_page(EVENT_BASE)
    while True:
        for event in page.find_all("div", class_="group_event_inner"):
            events.append(Event.load_from_html(event))

        page = visit_next(EVENT_BASE, page)
        if not page:
            break

    return events


if __name__ == "__main__":
    members = get_group_members()
    events = get_group_events()
