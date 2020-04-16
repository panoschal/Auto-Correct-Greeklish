from hunspell import Hunspell
from pynput import keyboard, mouse
from time import sleep, time
from language_monitor import detect_current_language
import collections


en = Hunspell('en_US', hunspell_data_dir='./data/hunspell_dictionaries')
el = Hunspell('el_GR', hunspell_data_dir='./data/hunspell_dictionaries')

controller = keyboard.Controller()

language_of_previous_word = 'en'


greek_letters = 'αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩς'
greek_accented = 'άέήίϊΐόύϋΰώΆΈΉΊΌΎΏ'
english_letters = 'abcdefghijklmnopqrstuvwxyz'
letters = greek_letters + greek_accented + english_letters + english_letters.upper()
letters_extended = letters + ' ;'

freq_en = []
with open('data/google_10000/google_sfw.txt') as google:
    for word in google.readlines():
        freq_en.append(word[:-1])


def find_language(string):
    for letter in greek_letters:
        if letter in string:
            return 'el'
    return 'en'


def validate_word(string):
    for character in string:
        if character not in letters_extended:
            return False
    return True


def is_letter(key):
    s = str(key)
    return len(s) == 3 and s[0] == "'" and s[2] == "'" and str(key)[1] in letters_extended


def execute_replacement(last_line, suggestion, ending_char):
    global cancel, manager
    print(last_line + '->' + suggestion)

    if cancel:
        print('cancel key pressed, I wont replace it')
        return

    manager.active = False
    # controller.press(keyboard.Key.left)
    # controller.release(keyboard.Key.left)
    # controller.press(keyboard.Key.ctrl)
    controller.press(keyboard.Key.backspace)
    controller.release(keyboard.Key.backspace)
    # controller.release(keyboard.Key.ctrl)
    for i in last_line:
        controller.press(keyboard.Key.backspace)
        controller.release(keyboard.Key.backspace)

    controller.type(suggestion)
    controller.press(ending_char)
    controller.release(ending_char)
    manager.active = True


def greek(word: str):

    lookup_table = ''.maketrans("qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM;", ";ςερτυθιοπασδφγηξκλζχψωβνμ:ΣΕΡΤΥΘΙΟΠΑΣΔΦΓΗΞΚΛΖΧΨΩΒΝΜ;")

    def stress(letter):
        dic = {el: el_stressed for el, el_stressed in zip(
            "ευιοαηω", "έύίόάήώ")}
        return dic[letter]

    gr = word.translate(lookup_table)
    gr_stress = ""
    for i in range(len(gr)):
        if gr[i] == ';' and i + 1 < len(gr) and gr[i+1] in "ευιοαηω":
            gr_stress = gr_stress + stress(gr[i + 1])
        if ((i > 0 and gr[i - 1] != ';')or i == 0) and gr[i] in greek_letters+greek_accented:
            gr_stress = gr_stress + gr[i]

    return gr_stress

# @TODO ignore my workflowy words
# @TODO some key combinations


def spellcheck(last_line):
    global language_of_previous_word

    def diff(original, suggestion):
        if len(suggestion) == 0:
            return 0  # or ZeroDivisionError
        count = 0
        for l in suggestion:
            if l in original:
                count += 1
        return count / len(suggestion)

    def closer_suggestion(my_list):
        out = [(diff(original, suggestion), suggestion)
               for original, suggestion in my_list]
        if out[0][0] > out[1][0]:
            return out[0][1]
        else:
            return out[1][1]

    def similar(original, suggestion):
        count = 0
        for l in suggestion:
            if l in original:
                count += 1
        res = (count >= len(original)-2) and (-1 <=
                                              len(original)-len(suggestion) <= 1)
        if not res:
            print(suggestion, 'not similar to', original)
        return res

    if last_line == '':
        return None

    lang = find_language(last_line)
    if lang == 'el' or detect_current_language() == 'el':
        return None

    common = {'toy': 'του', 'den': 'δεν',
              'myo': 'μου', 'alla': 'αλλα', 'ta': 'τα', 'soy': 'σου', 'ti': 'τι'}
    common_ambiguity = {'me': 'με', 'to': 'το', 'an': 'αν'}
    if last_line in common:
        suggestion = common[last_line]
        language_of_previous_word = find_language(suggestion)
        return suggestion
    if last_line in common_ambiguity and language_of_previous_word == 'el':
        suggestion = common_ambiguity[last_line]
        language_of_previous_word = find_language(suggestion)
        return suggestion

    isCorrect = en.spell(last_line)
    if isCorrect:
        language_of_previous_word = 'en'
        return None
    if (not isCorrect) and validate_word(last_line):
        suggestions_en = [word for word in en.suggest(last_line) 
            if word in freq_en and similar(last_line, word)]

        if el.spell(greek(last_line)):
            suggestions_el = [greek(last_line)]
        else:
            suggestions_el = [word for word in el.suggest(
                greek(last_line)) if similar(greek(last_line), word)]
        if len(suggestions_en) == 0 and len(suggestions_el) == 0:
            print('no suggestions for', last_line)
            return None
        elif len(suggestions_en) > 0 and len(suggestions_el) == 0:
            suggestion = suggestions_en[0]
        elif len(suggestions_en) == 0 and len(suggestions_el) > 0:
            suggestion = suggestions_el[0]
        elif len(suggestions_en) > 0 and len(suggestions_el) > 0:
            suggestion_en = suggestions_en[0]
            suggestion_el = suggestions_el[0]
            suggestion = closer_suggestion(
                [(last_line, suggestion_en), (greek(last_line), suggestion_el)])

        
        language_of_previous_word = find_language(suggestion)
        return suggestion

def keys_from_chars(string: str) -> list:
    return [keyboard.KeyCode.from_char(char) for char in string]

def on_press(key):
    if key in [keyboard.Key.space, *keys_from_chars('.,)-:!"]')]:
        ...
        cancel = False
        current_word = ''
        

from dataclasses import dataclass
@dataclass
class InputEvent:
    device: str
    key: keyboard.Key = None

import rx
from rx.subject import Subject
from rx import operators as ops

class Manager:

    def __init__(self):
        self.subject = Subject()
        self.input_stream = self.subject.subscribe()
        self.active = True

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.subject.on_next(InputEvent(device='mouse')) # send message to the subscribers

    def on_press(self, key):
        if self.active:
            self.subject.on_next(InputEvent(device='keyboard', key=key))
        if key == keyboard.Key.esc:
            self.subject.on_completed()
            raise SystemExit


if __name__ == '__main__':
    try:
        manager = Manager() 


        def calc_cancel(previous_event, event):
            if event.device == 'mouse':
                return True

            if event.key in [keyboard.Key.enter, keyboard.Key.tab]:
                return False
            if event.key in [keyboard.Key.backspace]:
                if previous_event.key in [keyboard.Key.space, *keys_from_chars('.,)-:!"]')]:  # πριν, πάτησα κενό, οπότε ακυρώνω για να γράψει ο χρήστης ότι θέλει
                    return True
                else:
                    return False
            if event.key in [keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down, *keys_from_chars('@#')]:
                return True

            return False # base case

        cancel = manager.subject.pipe(
            ops.pairwise(),
            ops.map(lambda pair_of_events: calc_cancel(*pair_of_events)),
            ops.start_with(False)
        )
        
        def keep_current_word(previous_word: str, t: tuple):
            print(f'keep_current_word with {previous_word}, {t}')
            event, cancel = t
            if event.device == 'mouse':
                return ''

            if cancel == False:
                if is_letter(event.key):
                    return previous_word + str(event.key)[1]

            if event.key in [keyboard.Key.enter, keyboard.Key.tab, keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down, *keys_from_chars('@#')]:
                return ''
            if event.key in [keyboard.Key.backspace]:
                if previous_word == '': # πριν, πάτησα κενό, οπότε ακυρώνω για να γράψει ο χρήστης ότι θέλει
                    return ''
                else:
                    return previous_word[:-1]
            
            return previous_word # nothing of the above
        current_word = manager.subject.pipe(
            ops.zip(cancel),
            ops.scan(keep_current_word, ''),
            ops.do_action(lambda current_word: print(f'word: "{current_word}"'))
        )
    
    
 
        current_word.subscribe()
        cancel.subscribe()


        def wrap_spellcheck(event: InputEvent, current_word_value: str):
            start = time()
            suggestion = spellcheck(current_word_value)
            print(f'time to compute: {time() - start}')
            start = time()
            if suggestion is not None:
                execute_replacement(current_word_value, suggestion, ending_char=event.key)
            print(f'time to replace: {time() - start}')

        spellcheck_event = manager.subject.pipe(
            ops.filter(lambda event: event.key in [keyboard.Key.space, *keys_from_chars('.,)-:!"]')]),
            ops.with_latest_from(current_word)
            # ops.map(lambda event: (event.key, ))
        ).subscribe(lambda tup: wrap_spellcheck(*tup))


        

        mouse_listener = mouse.Listener(on_click=lambda x, y, button, pressed: manager.on_click(x, y, button, pressed))
        mouse_listener.start()
        with keyboard.Listener(on_press=lambda key: manager.on_press(key)) as listener:
            try:
                print('listener ready')
                listener.join()
            except KeyError as err: 
                print('error', err)   

    except KeyboardInterrupt:
        raise SystemExit
    except KeyError as e:
        print(e)

# @TODO add names, maybe from fb
# @TODO στην αρχή του listener πρέπει να είσαι στα αγγλικά
# @TODO να κάνει σωστά τα κεφαλαία-μικρά
# @TODO να κάνει και πολλές λέξεις μαζί. πχ καιαυτό -> και αυτό. κα ιαυτό -> και αυτό.
# @TODO να βελτιώσω την ταχύτητα. να ακυρώνεται η διόρθωση αν προλάβεις να αρχίσεις την επόμενη λέξη. ή να διορθώνονται πολλές λέξεις μαζί.
# @TODO greek by frequency, sort, or by similarity
# @TODO πιο γρήγορο
# @TODO να βάζει την τελεία πριν το κεν΄΄ο
# @TODO shortcut για να εισάγεις λέξη στο λεξικό.
# @TODO όταν περν΄΄αει αρκετή ΄΄ωρα, να ακυρ΄΄ωνεται.
# @TODO ctrl+backspace bug
# @TODO να σου αλλάζει και την γλώσσα όταν κάνεις transliteration
# @TODO mute listener όταν κάνω push ένα suggestion
# ops.replay(buffer_size=1) # persist the last value
# use detect_current_language()