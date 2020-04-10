from hunspell import Hunspell
from pynput import keyboard, mouse
from time import sleep, time
from language_monitor import detect_current_language
import collections


en = Hunspell('en_US', hunspell_data_dir='./data/hunspell_dictionaries')
el = Hunspell('el_GR', hunspell_data_dir='./data/hunspell_dictionaries')

controller = keyboard.Controller()

cancel = False
current_word = ''
deafen_listener = False
language_of_previous_word = 'en'


greek_letters = 'αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩς'
greek_accented = 'άέήίϊΐόύϋΰώΆΈΉΊΌΎΏ'
english_letters = 'abcdefghijklmnopqrstuvwxyz'
letters = greek_letters + greek_accented + english_letters + english_letters.upper()
letters_extended = letters + ' ;'

freq_en = []
with open('data/google_10000/google_sfw.txt', 'rt') as google:
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
    global deafen_listener
    print(last_line + '->' + suggestion)

    if cancel:
        print('cancel key pressed, I wont replace it')
        return
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


def spellcheck(last_line, ending_char):
    global deafen_listener, language_of_previous_word

    def diff(original, suggestion):
        if len(suggestion) == 0:
            return 0  # or ZeroDivisionError
        count = 0
        for l in suggestion:
            if l in original:
                count += 1
        return count / len(suggestion)

    def closer_suggestion(list):
        out = [(diff(original, suggestion), suggestion)
               for original, suggestion in list]
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
        return

    lang = find_language(last_line)
    if lang == 'el' or detect_current_language() == 'el':
        return

    common = {'toy': 'του', 'den': 'δεν',
              'myo': 'μου', 'alla': 'αλλα', 'ta': 'τα', 'soy': 'σου', 'ti': 'τι'}
    common_ambiguity = {'me': 'με', 'to': 'το', 'an': 'αν'}
    if last_line in common:
        suggestion = common[last_line]
        language_of_previous_word = find_language(suggestion)
        execute_replacement(last_line, suggestion, ending_char=ending_char)
        return
    if last_line in common_ambiguity and language_of_previous_word == 'el':
        suggestion = common_ambiguity[last_line]
        language_of_previous_word = find_language(suggestion)
        execute_replacement(last_line, suggestion, ending_char=ending_char)
        return

    en.suggest(last_line)
    isCorrect = en.spell(last_line)
    if isCorrect:
        language_of_previous_word = 'en'
        # print('is correct in english')
        return
    if (not isCorrect) and validate_word(last_line):
        suggestions_en = [word for word in en.suggest(
            last_line) if word in freq_en and similar(last_line, word)]
        if el.spell(greek(last_line)):
            suggestions_el = [greek(last_line)]
        else:
            suggestions_el = [word for word in el.suggest(
                greek(last_line)) if similar(greek(last_line), word)]
        if len(suggestions_en) == 0 and len(suggestions_el) == 0:
            print('no suggestions for', last_line)
            return
        elif len(suggestions_en) > 0 and len(suggestions_el) == 0:
            suggestion = suggestions_en[0]
        elif len(suggestions_en) == 0 and len(suggestions_el) > 0:
            suggestion = suggestions_el[0]
        elif len(suggestions_en) > 0 and len(suggestions_el) > 0:
            suggestion_en = suggestions_en[0]
            suggestion_el = suggestions_el[0]
            suggestion = closer_suggestion(
                [(last_line, suggestion_en), (greek(last_line), suggestion_el)])

        # @TODO να σου αλλάζει και την γλώσσα όταν κάνεις transliteration
        # @TODO mute listener όταν κάνω push ένα suggestion
        language_of_previous_word = find_language(suggestion)
        execute_replacement(last_line, suggestion, ending_char=ending_char)


def on_press(key):
    global cancel, current_word, deafen_listener  # , listener
    if key == keyboard.Key.alt_gr:
        return False
    if deafen_listener:
        print('deafen listener True')
    else:
        try:
            # detect_current_language()
            # print(repr(key))
            # @TODO ctrl+backspace bug
            if cancel == False:
                if is_letter(key):
                    current_word = current_word + str(key)[1]
            if key in [keyboard.Key.left, keyboard.Key.right, keyboard.Key.up, keyboard.Key.down, keyboard.KeyCode.from_char('@'), keyboard.KeyCode.from_char('#')]:
                cancel = True
                current_word = ''
            if key in [keyboard.Key.space, keyboard.KeyCode.from_char('.'), keyboard.KeyCode.from_char(','), keyboard.KeyCode.from_char(')'), keyboard.KeyCode.from_char('-'), keyboard.KeyCode.from_char(':'), keyboard.KeyCode.from_char('!'), keyboard.KeyCode.from_char('"'), keyboard.KeyCode.from_char(']')]:
                deafen_listener = True
                start = time()
                spellcheck(current_word, ending_char=key)
                print('time:', str(time() - start))
                deafen_listener = False
                cancel = False
                current_word = ''
            if key in [keyboard.Key.enter, keyboard.Key.tab]:
                cancel = False
                current_word = ''
            if key in [keyboard.Key.backspace]:
                if current_word == '':  # πριν, πάτησα κενό, οπότε ακυρώνω για να γράψει ο χρήστης ότι θέλει
                    cancel = True
                    current_word = ''
                else:
                    cancel = False
                    current_word = current_word[:-1]
            print('word: "', current_word, '"', sep='')
        except KeyboardInterrupt:
            raise SystemExit
        except KeyError as e:
            print(e)


def on_click(x, y, button, pressed):
    global cancel, current_word
    cancel = True
    current_word = ''


mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

try:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
except KeyError as err:
    print('error', err)
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     listener.stop()

# later:
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