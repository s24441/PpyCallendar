from datetime import datetime
from pynput import keyboard
from typing import Callable
from enum import Enum
import os
import re

calendar_path = 'calendar.dat'
main_clndr = None

class Validation(Enum):
    DATE = 1
    TIME = 2


class Priority:
    LOW = 'L'
    NORMAL = 'N'
    HIGH = 'H'

    @staticmethod
    def compare(left: str, right: str):
        p_map = {Priority.LOW: 0, Priority.NORMAL: 1, Priority.HIGH: 2}
        return p_map[right] - p_map[left]


def clrscr():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_priority_from_user() -> str:
    print('\t[F3] Niski\n\t[F4] Normalny\n\t[F5] Wysoki\n\tWybierz priorytet (domyślnie - Normalny): ')
    p = Priority.NORMAL
    with keyboard.Events() as events:
        for event in events:
            if type(event) is keyboard.Events.Press:
                match event.key:
                    case keyboard.Key.f3:
                        p = Priority.LOW
                        break
                    case keyboard.Key.f5:
                        p = Priority.HIGH
                        break
                    case _:
                        break
    return p


class CalendarEvent:
    day_format = '%Y-%m-%d'
    time_format = '%H:%M:%S'
    datetime_format = '%Y-%m-%d %H:%M:%S'

    @staticmethod
    def validate(date_string: str, validation: Validation) -> bool:
        try:
            match validation:
                case Validation.DATE:
                    datetime.strptime(date_string, CalendarEvent.day_format)
                case Validation.TIME:
                    datetime.strptime(date_string, CalendarEvent.time_format)
                case _:
                    return False
            return True
        except ValueError:
            return False

    @staticmethod
    def create(row):
        # type: (str) -> CalendarEvent
        row += ';'
        data = row.split(';', 3)
        result = CalendarEvent(data[0], data[1], data[2])
        act = result
        depth = 1
        while len(data := data[3].split(';', 3)) > 3:
            match depth:
                case 1:
                    frmt = CalendarEvent.day_format
                case 2:
                    frmt = CalendarEvent.time_format
                case _:
                    frmt = None
            act.add_event(act := CalendarEvent(data[0], data[1], data[2], frmt))
            depth += 1
        return result

    @staticmethod
    def recreate(data):
        # type: (str) -> CalendarEvent
        result = None
        rows = data.split('\n')
        for row in rows:
            if row != '':
                if result is None:
                    result = CalendarEvent.create(row)
                else:
                    new_evt = CalendarEvent.create(row)
                    result.add_event(new_evt)
        return result

    def __init__(self, name: str, key_string: str, priority=Priority.NORMAL, key_format=None):
        self.name = name
        self.format = key_format
        self.dt = self.__key_match__(key_string, self.format)
        self.priority = priority
        self.orig_priority = self.priority
        self.parent = None
        self.sub_events = dict()

    def __key_match__(self, key: str, key_format: str):
        if key_format is None:
            return key
        else:
            return datetime.strptime(key, self.format)

    def __get_key__(self) -> str:
        if self.format is None or isinstance(self.dt, str):
            return self.dt
        else:
            return self.dt.strftime(self.format)

    def __info__(self) -> str:
        key = self.__get_key__() if self.format is not None else ''
        return f'{key}[{self.priority}{("(" + self.orig_priority + ")") if self.orig_priority != self.priority else ""}]: {self.name if self.name != key else ""}'

    def __propagate_priority__(self):
        if self.parent is not None:
            if Priority.compare(self.parent.priority, self.priority) > 0:
                self.parent.priority = self.priority
            self.parent.__propagate_priority__()

    def __restore_original_priority__(self):
        self.priority = self.orig_priority
        if self.parent is not None:
            self.parent.__restore_original_priority__()

    def __check_for_priority_restore__(self) -> str:
        max_priority = self.orig_priority

        for key, evt in self.sub_events.items():
            evt_subs_priority = evt.__check_for_priority_restore__()
            evt_priority = evt_subs_priority if Priority.compare(evt.priority, evt_subs_priority) > 0 else evt.priority
            if isinstance(evt, CalendarEvent) and Priority.compare(max_priority, evt_priority) > 0:
                max_priority = evt.priority
                if max_priority == Priority.HIGH:
                    break

        if Priority.compare(max_priority, self.priority) > 0:
            self.__restore_original_priority__()

        return max_priority

    def add_event(self, new_event):
        if isinstance(new_event, CalendarEvent):
            if new_event.__get_key__() == self.__get_key__():
                for evt in new_event.sub_events.values():
                    if evt.__get_key__() in self.sub_events:
                        self.sub_events[evt.__get_key__()].add_event(evt)
                    else:
                        self.add_event(evt)
            else:
                nv_key = new_event.__get_key__()
                self.sub_events[nv_key] = new_event
                new_event.parent = self
                new_event.__propagate_priority__()

    def remove_event(self, datetime_string: str):
        self.sub_events.pop(datetime_string)
        self.__check_for_priority_restore__()
        self.__propagate_priority__()
        act = self
        while act is not None and act.format != CalendarEvent.day_format:
            act = act.parent
        if act is not None:
            act.__check_for_priority_restore__()

    def set_priority(self, new_priority: str):
        self.orig_priority = new_priority
        if Priority.compare(self.priority, self.orig_priority) > 0 or len(self.sub_events) == 0:
            self.priority = self.orig_priority
        self.__propagate_priority__()
        act = self.parent
        while act is not None and act.format != CalendarEvent.day_format:
            act = act.parent
        act.__check_for_priority_restore__()

    # nawigacja w formie generatora kontrolowanego przez klawisze przechwytywane przez pynput
    def navigate(self):
        # type: () -> CalendarEvent
        actual, i, keys, last = self, -1, [], -1

        if len(self.sub_events) < 1:
            nd = datetime.now().strftime(CalendarEvent.day_format)
            self.add_event(CalendarEvent(nd, nd, key_format=CalendarEvent.day_format))

        def reset(to_key=None):
            nonlocal i, last, keys, actual
            keys = list(sorted(actual.sub_events.keys()))
            i = 0
            if to_key is not None:
                j = 0
                for k in keys:
                    if k == to_key:
                        i = j
                        break
                    j += 1
            last = len(keys) - 1

        def go_up():
            nonlocal actual
            if actual.parent is not None:
                k = actual.__get_key__()
                actual = actual.parent
                reset(k)

        starting_key = None
        now = datetime.now()
        start_date = None
        tmp_diff = None
        for key in actual.sub_events.keys():
            dt = datetime.strptime(key, CalendarEvent.day_format)
            diff = now - dt if now > dt else dt - now
            if tmp_diff is None or diff < tmp_diff:
                start_date = dt
                tmp_diff = diff

        if start_date is not None:
            starting_key = start_date.strftime(CalendarEvent.day_format)

        reset(starting_key)

        stopping_token = last == -1
        while not stopping_token:
            if last == -1:
                print('Kalendarz jest pusty')
                break
            PersistenceUtils.save_calendar(calendar_path, main_clndr)
            yield actual.sub_events[keys[i]]

            action = None

            with keyboard.Events() as events:
                for event in events:
                    if type(event) is keyboard.Events.Press:
                        match event.key:
                            case keyboard.Key.up:
                                go_up()
                                break
                            case keyboard.Key.left:
                                i = i - 1 if i > 0 else last
                                break
                            case keyboard.Key.right:
                                i = (i + 1) % (last + 1)
                                break
                            case keyboard.Key.down:
                                if len(actual.sub_events[keys[i]].sub_events) > 0:
                                    actual = actual.sub_events[keys[i]]
                                    reset()
                                break
                            case keyboard.Key.f11:
                                if actual.sub_events[keys[i]].format == CalendarEvent.day_format:
                                    action = 'ad'
                                break
                            case keyboard.Key.f12:
                                if actual.sub_events[keys[i]].format in [CalendarEvent.day_format, CalendarEvent.time_format]:
                                    action = 'a'
                                break
                            case keyboard.Key.esc:
                                stopping_token = True
                                break
                            case keyboard.Key.delete:
                                if action == 'd':
                                    actual.remove_event(keys[i])
                                    if len(actual.sub_events) < 1:
                                        go_up()
                                    else:
                                        reset(keys[(i + 1) % (last + 1)])
                                    break
                                if action is None:
                                    print('Czy usunąć wybrany event? [Tak-DEL/Nie-ENTER]')
                                    action = 'd'
                            case keyboard.Key.enter:
                                if action == 'd':
                                    break
                            case keyboard.Key.backspace:
                                if action is None:
                                    action = 'e'
                                    break
                            case _:
                                pass

            if action == 'ad':
                valid_token = False
                ndate = None
                while not valid_token:
                    ndate = input('Podaj datę w formacie "yyyy-mm-dd": ')
                    valid_token = CalendarEvent.validate(ndate, Validation.DATE)
                    if not valid_token:
                        print(f'Podana data {ndate} ma zły format')
                    else:
                        if not (valid_token := ndate not in actual.sub_events.keys()):
                            print(f'Podana data już istnieje')
                p = get_priority_from_user()
                actual.add_event(CalendarEvent(ndate, ndate, p, CalendarEvent.day_format))
                reset(ndate)
            while action == 'a':
                match actual.sub_events[keys[i]].format:
                    case CalendarEvent.day_format:
                        valid_token = False
                        time = None
                        while not valid_token:
                            time = input('Podaj godzinę w formacie "hh:mm:ss": ')
                            valid_token = CalendarEvent.validate(time, Validation.TIME)
                            if not valid_token:
                                print(f'Podany czas {time} ma zły format')
                            else:
                                if not (valid_token := time not in actual.sub_events[keys[i]].sub_events.keys()):
                                    print(f'Istnieje już event odbywający się w podanym czasie')
                        event_name = input('Podaj nazwę wydarzenia: ')
                        p = get_priority_from_user()
                        actual.sub_events[keys[i]].add_event(
                            CalendarEvent(event_name, time, p, CalendarEvent.time_format))
                        break
                    case CalendarEvent.time_format:
                        step_name = input('Podaj nazwę kroku: ')
                        p = get_priority_from_user()
                        actual.sub_events[keys[i]].add_event(
                            CalendarEvent(step_name, str(len(actual.sub_events[keys[i]].sub_events)), p))
                        break

            while action == 'e':
                match actual.sub_events[keys[i]].format:
                    case CalendarEvent.day_format:
                        while not CalendarEvent.validate(
                                (date := input('Podaj nową datę w formacie yyyy-mm-dd (Anuluj-pusta wartość): ')),
                                Validation.DATE) and date != '':
                            print('Podano nieprawidłową datę')
                        obj = actual.sub_events[keys[i]]
                        obj.name = date
                        obj.dt = obj.__key_match__(date, obj.format)
                        actual.sub_events[date] = actual.sub_events.pop(keys[i])
                        reset(obj.__get_key__())
                        break
                    case CalendarEvent.time_format:
                        print('[F3] Zmień czas\n[F4] Zmień nazwę\n[F5] Zmień priorytet\n[ESC] Anuluj')
                        edit = None
                        with keyboard.Events() as events:
                            for event in events:
                                if type(event) is keyboard.Events.Press:
                                    match event.key:
                                        case keyboard.Key.f3:
                                            edit = 'time'
                                            break
                                        case keyboard.Key.f4:
                                            edit = 'name'
                                            break
                                        case keyboard.Key.f5:
                                            edit = 'priority'
                                            break
                                        case keyboard.Key.esc:
                                            break
                                        case _:
                                            pass
                        match edit:
                            case 'time':
                                while not CalendarEvent.validate(
                                        (time := input(
                                            'Podaj nowy czas w formacie hh:mm:ss (Anuluj - pusta wartość): ')),
                                        Validation.TIME) and time != '':
                                    print('Podano nieprawidłowy czas')
                                obj = actual.sub_events[keys[i]]
                                obj.dt = obj.__key_match__(time, obj.format)
                                actual.sub_events[time] = actual.sub_events.pop(keys[i])
                                reset(obj.__get_key__())
                                break
                            case 'name':
                                name = input('Podaj nowy czas w formacie hh:mm:ss (Anuluj - pusta wartość): ')
                                if name != '':
                                    actual.sub_events[keys[i]].name = name
                                break
                            case 'priority':
                                actual.sub_events[keys[i]].set_priority(get_priority_from_user())
                                break
                            case _:
                                break
                    case _:
                        print('[F4] Zmień nazwę\n[F5] Zmień priorytet\n[ESC] Anuluj')
                        edit = None
                        with keyboard.Events() as events:
                            for event in events:
                                if type(event) is keyboard.Events.Press:
                                    match event.key:
                                        case keyboard.Key.f3:
                                            edit = 'order'
                                            break
                                        case keyboard.Key.f4:
                                            edit = 'name'
                                            break
                                        case keyboard.Key.f5:
                                            edit = 'priority'
                                            break
                                        case keyboard.Key.esc:
                                            break
                                        case _:
                                            pass
                        match edit:
                            case 'order':
                                break
                            case 'name':
                                name = input('Podaj nową nazwę kroku (Anuluj - pusta wartość): ')
                                if name != '':
                                    actual.sub_events[keys[i]].name = name
                                break
                            case 'priority':
                                actual.sub_events[keys[i]].set_priority(get_priority_from_user())
                                break
                            case _:
                                break

    def delete_events(self, predicate, pagination='', prefix=''):
        # type: (Callable[[CalendarEvent], bool], str, str) -> None
        msg = f'{prefix}{pagination}-{self.__info__()}\n' if self.parent is not None else ''
        node_found = predicate(self)
        if node_found:
            print(msg)
            d = input('Usunąć event? [T-tak/N-nie] ')
            if d == 'T':
                self.parent.remove_event(self.__get_key__())
        else:
            for key, item in sorted(self.sub_events.items()):
                item.delete_events(predicate, pagination + '\t', msg)

    def show_sub_events(self, pagination='', predicate=None, starter=None, info_prefix=''):
        # type: (str, Callable[[CalendarEvent], bool], CalendarEvent, int) -> str | bool
        prefix = f'{info_prefix}' # {"(ord=" + self.__get_key__() + ")" if info_prefix != "" else ""}
        msg = f'{pagination}-{prefix}{self.__info__()}\n' if self.parent is not None else ''

        should_print = predicate is None
        node_found = not should_print and predicate(self)
        cnt = 0
        for key, item in sorted(self.sub_events.items()):
            if item.format is None:
                cnt += 1
            sub_msg = item.show_sub_events(pagination + '\t', None if node_found else predicate, info_prefix=cnt if cnt != 0 else '')
            if sub_msg:
                msg += sub_msg
                should_print = True

        if self.parent is None or self == starter:
            if should_print:
                print(msg)
                msg = True
            else:
                print('Nie znaleziono wyników')
                msg = False

        return msg if should_print or predicate is not None and predicate(self) else False

    def to_str(self, prefix: str = '', flat: bool = False) -> str:
        prfx = f'{prefix}{self.name};{self.__get_key__()};{self.orig_priority}'
        if flat is True:
            return prfx
        cnt = len(self.sub_events)
        rsl = ''
        if cnt > 0:
            end = ';'
            for key, val in sorted(self.sub_events.items()):
                rsl += f'{val.to_str(prfx+end)}'
        else:
            end = '\n'
            rsl = f'{prfx}{end}'
        return rsl


class PersistenceUtils:

    @staticmethod
    def load_calendar(path: str) -> CalendarEvent:
        result = None
        if os.path.isfile(path):
            with open(path, 'r') as data:
                content = data.read()
                if content != '':
                    result = CalendarEvent.recreate(content)
        else:
            with open(path, 'w') as data:
                data.write("")

        return result

    @staticmethod
    def save_calendar(path: str, calendar: CalendarEvent):
        content = ''
        if calendar is not None:
            content = calendar.to_str()
        with open(path, 'w') as data:
            data.write(content)


def main():
    global main_clndr
    main_clndr \
        = PersistenceUtils.load_calendar(calendar_path)
    if main_clndr is None:
        main_clndr = CalendarEvent.create(f'PpyCallendar;{None};{Priority.NORMAL}')

    stopping_token = False
    while not stopping_token:
        clrscr()
        print('[F3] Pokaż kalendarz\n[F4] Znajdź wydarzenia\n[F5] Usuń wydarzenia\n[ESC] Zakończ')
        decision = None
        with keyboard.Events() as events:
            for event in events:
                if type(event) is keyboard.Events.Press:
                    match event.key:
                        case keyboard.Key.f3:
                            decision = 'navigate'
                            break
                        case keyboard.Key.f4:
                            decision = 'filter'
                            break
                        case keyboard.Key.f5:
                            decision = 'filter.delete'
                            break
                        case keyboard.Key.esc:
                            decision = 'end'
                            break
                        case _:
                            pass
        match decision:
            case 'navigate':
                for act in main_clndr.navigate():
                    clrscr()
                    print(f'[UP] Powrót, [DWN] Sub-eventy, [<-] Poprzedni, [->] Nastepny, '
                          f'{"[F11] Dodaj datę, [F12] Dodaj wydarzenie, " if act.format == CalendarEvent.day_format else ""}'
                          f'{"[F12] Dodaj krok wydarzenia, " if act.format == CalendarEvent.time_format else ""}'
                          f'[BCKPSP] Edytuj, [DEL] Usuń, [ESC] Wyjdź''')
                    act.show_sub_events(starter=act)
                PersistenceUtils.save_calendar(calendar_path, main_clndr)
            case 'filter':
                query_string = input('Podaj nazwę wydarzenia/kroku lub datę w formacie yyyy-mm-dd: ')
                main_clndr.show_sub_events(
                    predicate=lambda x: isinstance(x, CalendarEvent) and re.search(query_string.lower(),
                                                                                   x.name.lower()) is not None)
            case 'filter.delete':
                query_string = input('Podaj nazwę wydarzenia/kroku lub datę w formacie yyyy-mm-dd: ')
                main_clndr.delete_events(
                    predicate=lambda x: isinstance(x, CalendarEvent) and re.search(query_string.lower(),
                                                                                   x.name.lower()) is not None)
                PersistenceUtils.save_calendar(calendar_path, main_clndr)
            case 'end':
                stopping_token = True
            case _:
                pass
        if decision != 'end':
            print('[Naciśnij ENTER aby kontynuować]')
            with keyboard.Events() as events:
                for event in events:
                    if type(event) is keyboard.Events.Press and event.key == keyboard.Key.enter:
                        break

    PersistenceUtils.save_calendar(calendar_path, main_clndr)


if __name__ == '__main__':
    main()
