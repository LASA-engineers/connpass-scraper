import csv
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
        idstr = parse_idstr(link["href"])
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


def parse_idstr(s):
    return re.compile(r"^https?://connpass.com/user/([^/]+)/.*$").search(s).group(1)


def parse_date(s):
    if not s:
        return s
    return re.compile(r"^(\d{4}/\d{2}/\d{2}).*$").search(s).group(1)


def get_page(url):
    print(f"GET {url}")
    res = requests.get(url)
    time.sleep(3)
    if res.status_code == requests.codes.ok:
        return BeautifulSoup(res.content, "html.parser")
    else:
        return None


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
        members += [Member.load_from_html(member) for member in page.find_all("tr", class_="GroupMemberProfile")]

        page = visit_next(MEMBER_BASE, page)
        if not page:
            break

    return members


def get_group_events():
    events = []

    page = get_page(EVENT_BASE)
    while True:
        events += [Event.load_from_html(event) for event in page.find_all("div", class_="group_event_inner")]

        page = visit_next(EVENT_BASE, page)
        if not page:
            break

    return list(reversed(events))


def get_member_attendance(members, events):
    attendance = {member.idstr: [0] * len(events) for member in members}

    def set_attendance(table, i, a):
        for name in table.find_all("p", class_="display_name"):
            if name.find("a"):
                idstr = parse_idstr(name.a["href"])
                if idstr in attendance:
                    attendance[idstr][i] = a
                else:
                    print(f"unsubscribed user: {idstr}")
            else:
                print("withdrawn user")

    for i, event in enumerate(events):
        for member in members:
            if member.join > event.date:
                attendance[member.idstr][i] = -1

        page = get_page(event.url + "participation/")
        if not page:
            continue

        if page.find("div", class_="cancelled_table_area"):
            set_attendance(page.find("div", class_="cancelled_table_area").table, i, 1)

        set_attendance(page.find("div", class_="concerned_area"), i, 10)

        for div in page.find_all("div", class_="participation_table_area"):
            td = div.table.tbody.find_all("tr")[-1].find_all("td")
            if len(td) == 1:
                # no participants
                if td[0].text == "イベント申込者はいません。":
                    continue
                else:
                    # more than 100 participants; multiple pages
                    base = td[0].a["href"]
                    page = get_page(base)
                    while page:
                        set_attendance(page.find("div", class_="participation_table_area").table, i, 2)
                        page = visit_next(base, page)
            else:
                # single page
                set_attendance(div.table, i, 2)

    return attendance


def print_csv(members, events, attendance):
    with open("lasa-connpass.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",", quotechar="\"", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["ID", "name", "join", "count"] + [event.title for event in events])
        for member in members:
            writer.writerow([member.idstr, member.name, member.join, member.count] + attendance[member.idstr])


if __name__ == "__main__":
    members = get_group_members()
    events = get_group_events()
    attendance = get_member_attendance(members, events)
    print_csv(members, events, attendance)
