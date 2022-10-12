#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANAC is Not A Chain
This is not an analytic chain, but rather hub of a network of analytic tools, designed to process old Hungarian poems.
The program was developped during the OTKA K 135631 research at the Eötvös Loránd University, Budapest, Hungary, under the direction of Levente Seláf.

Created on Sun Feb 14 14:45:09 2021

@author: Andor Horváth
The code includes some lines of Eszter Simon.
"""

import json
import re
import subprocess
import pdc
import elonorm
import epitran
import os

unanalyzed = set()
unanalyzed_freq = dict()
unanalyzed_pos = list()
elonorm_hibak = dict()

rep = pdc.PDC(dbhost="***", dbuser="***",
                           dbpassword="***", dbname="***", selected=['RPHA'], verb=True)

def poemjson(text, poemid="", author="", title=""):
    """ Handles the JSON -compatible conversion of plain text poems
    that may be divided into parts.
    Returns a JSON-compatible object."""
    if("[part" not in text):
        json_stanzas = poemtextjson(text)
        return { "manually_checked": False,
                "poem_id": poemid,
                "poem_title": title,
                "poem_author": author,
                "stanzas": json_stanzas }
    else:
        parts = re.split('\n*(\[part)[ ]?["]?([^\]]*)["]?\]\n*', text)
        json_parts = []
        a = 0
        partnr = 0
        while a < len(parts):
            if(parts[a] == '[part'):
                partnr += 1
                parttitle = parts[a + 1]
                json_stanzas = poemtextjson(parts[a + 2])
                json_parts.append({ "part_number": partnr,
                                   "part_title": parttitle,
                                   "stanzas": json_stanzas })
                a += 3
            else:
                if(parts[a] != ''):
                    json_stanzas = poemtextjson(parts[a])
                    json_parts.append({ "part_number": "UNINDENTIFIED",
                                   "stanzas": json_stanzas })
                a += 1
        return { "manually_checked": False,
                "poem_id": poemid,
                "poem_title": title,
                "poem_author": author,
                "parts": json_parts }
                

def spacetounderscore(text):
    """ A quick'n'dirty solution for my embarassing RegEx problem. """
    return re.sub(r' ', r'_', text.group())

def poemtextjson(text):
    """ Handles the JSON-compatible conversion of plain text. """
    text = re.sub(r'\[[^\]]*\]', spacetounderscore, text)
    stanzas = text.split('\n\n')
    json_stanzas = []
    stanzanr = 0
    for stanza in stanzas:
        stanzanr += 1
        json_lines = []
        lines = stanza.split('\n')
        linenr = 0
        for line in lines:
            if('[miss' not in line):
                linenr += 1
                json_words = []
                words = line.split(' ')
                wordnr = 0
                for word in words:
                    word = re.sub(r'^[^A-zÖÜÓŐÚÉÁŰÍöüóőúéáűí]+', r'', word)
                    word = re.sub(r'[^A-zÖÜÓŐÚÉÁŰÍöüóőúéáűí]+$', r'', word) # Remove punctuation.
                    if(len(word)>0):
                        wordnr += 1
                        json_words.append({ "word_number": wordnr,
                         "word_text": word })
                if(len(json_words)>0):
                    json_lines.append({ "line_number": linenr,
                                       "line_text": line,
                                       "words": json_words })
            else:
                if('lines' in line):
                    missline = re.split('miss[_ ]\"', re.split('[_ ]lines', line)[0])[1]
                    if(missline == '?'):
                        missline = 0
                    else:
                        missline = int(missline)
                        linenr += missline
                        json_lines.append({ "missing_lines": missline })
        if(len(json_lines)>0):
            json_stanzas.append({"stanza_number": stanzanr,
                                 "lines": json_lines})
    return(json_stanzas)


# def analyze_demo(text):
#     """ Template for developing further analysis routines
#     on the POSTDATA-compatible JSON structures. """
#     errcode = 0 # An example variable that could be any type.
#     if("stanzas" in text):
#         for stanza in text["stanzas"]:
#             # Here are stuff you do with stanzas.
#             if("lines" in stanza):
#                 for line in stanza["lines"]:
#                     # Here are stuff you do with lines.
#                     if("words" in line):
#                         for word in line["words"]:
#                             if("word_text" in word):
#                                 # Here are stuff you do with words.
#                                 print(word["word_text"])
#                     # Here are also stuff you do with lines.
#             # Here are also stuff you do with stanzas.
#     return [text, errcode] # Just to show that these functions return the modified JSON and maybe some extra metadata.


def analyze_length(text):
    """ Counts the number of stanzas, lines and words in a JSON-compatible poem. """
    stanzas = 0
    lines = 0
    words = 0
    if("stanzas" in text):
        for stanza in text["stanzas"]:
            stanzas += 1
            if("lines" in stanza):
                for line in stanza["lines"]:
                    lines += 1
                    if("words" in line):
                        for word in line["words"]:
                            if("word_text" in word):
                                words += 1
    text["number_of_stanzas"] = stanzas
    text["number_of_lines"] = lines
    text["number_of_words"] = words
    return [text]


def analyze_wordstat(text):
    """ Counts the number of stanzas, lines and words in a JSON-compatible poem. """
    wordstat = dict()
    words = 0
    if("stanzas" in text):
        for stanza in text["stanzas"]:
            if("lines" in stanza):
                for line in stanza["lines"]:
                    if("words" in line):
                        for word in line["words"]:
                            if("lemma" in word):
                                if(("[N]" in word["morphology"] or "[V]" in word["morphology"] or "[Adv]" in word["morphology"] or "[Adj]" in word["morphology"]) and word["lemma"].lower() == word["lemma"]):
                                    words += 1
                                    if word["lemma"] not in wordstat:
                                        wordstat[word["lemma"]] = 1
                                    else:
                                        wordstat[word["lemma"]] += 1
    if(len(wordstat) == 0):
        text["wordstat"] = { "_vocabulary": 0, "_repetitivity": 1 }
    else:
        text["wordstat"] = { "_vocabulary": len(wordstat), "_repetitivity": words/len(wordstat) }
    wordstat = {key: val for key, val in sorted(wordstat.items(), key = lambda ele: ele[1], reverse=True)}
    for k in wordstat.keys():
        if(wordstat[k] > words/len(wordstat)):
            text["wordstat"][k] = wordstat[k]
    return [text]


def analyze_syll(text):
    """ Analyzes a JSON-compatible poem's syllabic structure
    and stores the results within the structure."""
    syllstat = dict()
    stressstat = dict()
    if("stanzas" in text):
        for stanza in text["stanzas"]:
            syllables = []
            if("lines" in stanza):
                for line in stanza["lines"]:
                    syllline = 0
                    stressline = 0
                    line["stress_pattern"] = ''
                    if("words" in line):
                        for word in line["words"]:
                            if("word_text" in word):
                                if(word == line["words"][-1]):
                                    word["rhyme"] = True
                                syllcount = len(re.findall(r'([aeiouűáéúőóüöíAEIOUŰÁÉÚŐÓÜÖÍ])', word["word_text"]))
                                word["syllable_count"] = syllcount # Syllable count of the current word.
                                syllline += syllcount
                                if(syllcount == 1):
                                    line["stress_pattern"] += '.' # One-syllable words count as unstressed. Watch out for the orthograph of prepositions!
                                if(syllcount > 1):
                                    line["stress_pattern"] += '|' # The first syllable is stressed in Hungarian.
                                    for c in range(syllcount-1):
                                        line["stress_pattern"] += '.' # Only the first syllable is stressed.
                    if("line_text" in line):    
                        linetext = line["line_text"]
                        linetext = re.sub(r'[ ,.;:!?\-–\'"…]', '', linetext)
                        # for a in range(len(linetext)):
                        #     if(linetext[a].lower() in ['a', 'e', 'i', 'o', 'u', 'ű', 'á', 'é', 'ú', 'ő', 'ó', 'ü', 'ö', 'í']):
                        #         if(
                        linetext = re.sub(r'([aeiouűáéúőóüöíAEIOUŰÁÉÚŐÓÜÖÍ])', r'|\1', linetext)
                        syll = linetext.split('|')
                        spatt = ''
                        for a in syll:
                            if(len(a) > 0):
                                if(a.lower()[0] in ['ű', 'á', 'é', 'ú', 'ő', 'ó', 'í']):
                                    spatt += '-'
                                if(a.lower()[0] in ['a', 'e', 'i', 'o', 'u', 'ü', 'ö']):
                                    # if(len(a) > 4 or (len(a) > 3 and 'dzs' not in a)):
                                    if(len(a) > 4 or (len(a) > 3 and 'dzs' not in a)):
                                        spatt += '-'
                                    if(len(a) < 3 or (len(a) == 4 and 'dzs' in a)):
                                        spatt += 'U'
                                    if(len(a) == 3):
                                        if(a[1:] not in ['cs', 'dz', 'gy', 'ly', 'ny', 'sz', 'ty', 'zs']):
                                            spatt += '-'
                                        else:
                                            spatt += 'U'
                                # print(a + '(' + spatt[-1] + ')', end='')
                        # print(spatt)
                        if(spatt[-1] == 'U'):
                            spatt = spatt[:-1] + '-' # The last syllable is always long.
                        # print(line["line_text"])
                        # for s in spatt:
                        #     print(s, end=' ')
                        # print('')
                        line["metric_pattern"] = spatt
                        if(syllline not in syllstat):
                            syllstat[syllline] = list()
                            for a in range(syllline):
                                syllstat[syllline].append(0)
                        if(syllline not in stressstat):
                            stressstat[syllline] = list()
                            for a in range(syllline):
                                stressstat[syllline].append(0)
                        # if(syllline > len(spatt)): # For debugging.
                        #     print(linetext)
                        #     print('! ' + str(syllline) + ' ' + str(len(spatt)))
                        for a in range(syllline):
                            if(spatt[a] == '-'):
                                syllstat[syllline][a] += 1
                        for a in range(syllline):
                            if(line["stress_pattern"][a] == '|'):
                                stressstat[syllline][a] += 1
                                stressline += 1
                    line["syllable_count"] = syllline # Syllable count of the current line.
                    line["stress_count"] = stressline # Stress count of the current line.
                    syllables.append(str(syllline))
            stanza["syllables"] = ', '.join(syllables) # Syllable pattern of the current stanza.
            # stanza["syllable_length_statistics"] = syllstat
    text["long_syllable_statistics"] = syllstat
    text["stressed_syllable_statistics"] = stressstat
    # print('')
    return [text]

def analyze_phonetic(text):
    """ Creates the phonetic transcription of a JSON-compatible poem
    and stores the results within the structure. """
    a = 0
    if("stanzas" in text):
        for stanza in text["stanzas"]:
            # Here are stuff you do with stanzas.
            if("lines" in stanza):
                for line in stanza["lines"]:
                    # Here are stuff you do with lines.
                    if("words" in line):
                        for word in line["words"]:
                            if("word_text" in word):
                                # Here are stuff you do with words.
                                # epi = epitran.Epitran('hun-Latn')
                                # epi = epi.transliterate(word["word_text"])
                                # epi = epi.replace('\n', ' ')
                                # epi = re.sub(' +', ' ', epi)
                                ipa = subprocess.check_output(["espeak", "-q", "--ipa", '-v', 'hu-hu', re.sub('^\-', '', word["word_text"])]).decode('utf-8')
                                ipa = ipa.replace('\n', ' ')
                                ipa = re.sub(' +', '', ipa)
                                a += 1
                                if(a >= 100):
                                    # print(word["word_text"] + '\t' + ipa)
                                    print('|', end='')
                                    a = 0
                                word["word_ipa_espeak"] = ipa
                    # Here are also stuff you do with lines.
            # Here are also stuff you do with stanzas.
    print('')
    return [text] # Just to show that these functions return the modified JSON and maybe some extra metadata.


def analyze_morph(text, normalizator):
    """ Analyzes a JSON-compatible poem's morphology
    and stores the results within the structure. """
    global unanalyzed_pos
    global elonorm_hibak
    wordlist = []
    wordcount = 0
    if(normalizator == 'tinodi'):
        memdict = {}
        charrules = dict()
    else:
        memdict = elonorm.memory_dict_from_file('elonorm/' + normalizator + '_szotar.csv')
        charrules = elonorm.char_rules_from_file('elonorm/' + normalizator + '_char_subs.csv')
    file = open('elonorm/proper_names.csv', "r")
    properlist = file.readlines()
    file.close()
    k = 0
    if("stanzas" in text):
        for stanza in text["stanzas"]:
            if("lines" in stanza):
                for line in stanza["lines"]:
                    if("words" in line):
                        a = 0
                        for word in line["words"]:
                            a += 1
                            if("word_text" in word):
                                wordtext = word["word_text"]
                                wordcount += 1
                                proper = False
                                for name in properlist:
                                    if(wordtext.startswith(name.replace('\n', '')) == True):
                                        proper = True
                                        print(line["line_text"])
                                        print("Tulajdonnév: " + wordtext)
                                if wordtext in memdict:
                                    ''' Memory-based normalization, stores case. '''
                                    wordnorm = memdict[wordtext].strip('\n')
                                elif proper == False:
                                    ''' Character-level rewrite rules, lowercase
                                    if first word in line. '''
                                    wordnorm = elonorm.regex_sub(wordtext.lower(), charrules)
                                    if(wordtext[0].lower() != wordtext[0]):
                                        wordnorm = wordnorm[0].upper() + wordnorm[1:]
                                if(wordnorm != wordtext or proper == True):
                                    word["word_text_normalized"] = wordnorm
                                    k += 1
                                else:
                                    if("word_text_normalized" in word):
                                        word.pop("word_text_normalized")
                                wordlist.append(wordnorm)
                    wordlist.append('[EOL]')
                wordlist.append('[EOS]')

        """ Morphological analysis. """
        file = open("morph.tmp", "w")
        file.write('\n'.join(wordlist))
        file.close()
        morph = subprocess.check_output("hfst-lookup --pipe-mode=input --cascade=composition emMorphOMH_distrib/hfst/OMH.hfstol < morph.tmp", shell=True, executable="/bin/bash").decode()
        
        file = open("morphout.tmp", "w")
        file2 = open("morphout2.tmp", "w")
        morwords = morph.split('\n\n')
        # Here we write the morphological analysis into the morphout.tmp file, but without
        # any solution with a derivational suffix (so anything that contains '[_'.
        # Words that only contain such solutions will be left intact, though.
        morphnoderiv = ''
        for mword in morwords:
            mw = re.sub(r'.+\[_.*\n*', r'', mword)
            if(len(mw)>0):
                file.write(mw)
                morphnoderiv += mw
            else:
                file.write(mword)
                morphnoderiv += mword
            file2.write(mword)
            file2.write('\n\n')
            file.write('\n\n')
            morphnoderiv += '\n\n'
        # file.write(morph)
        file2.close()
        file.close()        
        morphpure = convert(morphnoderiv)

        """ Morphological disambiguation. """
        file = open("morph.tmp", "w")
        file.write(morphpure)
        file.close()
        morphcomm = "java -jar purepos/purepos-2.1.one-jar.jar tag -a none -m purepos/omh.model -i morph.tmp"
        # morphcomm = 'echo "' + morphpure + '" | java -jar purepos/purepos-2.1.one-jar.jar tag -a none -m purepos/omh.model -i morph.tmp'
        puretext = subprocess.check_output(morphcomm, shell=True, executable="/bin/bash").decode()
        file = open("pure.tmp", "w")
        file.write(puretext)
        file.close()
        # os.remove("morph.tmp")

        """ Storing the data in the JSON structure. """
        puretext = re.sub(r'\n', ' ', puretext)
        purelist = puretext.split(' ')
        # purelist = re.sub(r'\n\n', r'\n', puretext).split(' ')
        hib = len(re.findall(r'\+\?', morph))
        i = 0
        j = 0
        errlist = set()
        for stanza in text["stanzas"]:
            if("lines" in stanza):
                for line in stanza["lines"]:
                    if("words" in line):
                        for word in line["words"]:
                            if("word_text" in word):
                                pure = purelist[i].split('#')
                                if(len(pure) == 3):
                                    if('?' not in pure[2]):
                                        word["lemma"] = pure[1]
                                        if(len(pure[2]) > 1):
                                            if('[' in pure[2]):
                                                morin = pure[2][1:-1] # Why is this doing the right thing in case of properly analyzed words, and not the right thing with the guesser?
                                                # morin = pure[2]
                                            else:
                                                morin = pure[2]
                                        else:
                                            morin = pure[2]
                                        morout = ""
                                        for mor in morin.split(':'):
                                            if(len(mor)>0):
                                                morout = morout + "[" + mor + "]"
                                        word["morphology"] = morout
                                        # print(word["word_text"] + '\t' + word["lemma"] + '\t' + word["morphology"])
                                        j += 1 # counting the successful analyses
                                    else:
                                        # print('Error: ' + pure[0])
                                        errlist.add('!' + '\t' + pure[0] + '\t' + pure[1] + '\t' + pure[2])
                                i += 1
                                if(i in unanalyzed_pos):
                                    word["morphology_guessed"] = True
                                    if("word_text_normalized" in word):
                                        if(word["word_text"] not in elonorm_hibak):
                                            elonorm_hibak[word["word_text"]] = [word["word_text_normalized"], 1]
                                        else:
                                            elonorm_hibak[word["word_text"]][1] += 1                                       
    if(wordcount>0):
        print('Words: ' + str(wordcount) + '\t\tGuessed: ' + str(hib) + ' (' + str(round(hib*100/wordcount)) + '%)\t\tPrenormalized: ' + str(round(k*100/wordcount)) + '%')
    return [text, errlist]


def sum_parts(text):
    """ Sums certain analytics of a poem's parts. """
    syllstat = dict()
    stressstat = dict()
    wordstat = dict()
    stanzas = 0
    lines = 0
    words = 0
    if("parts" in text):
        for part in text["parts"]:
            if("long_syllable_statistics" in part):
                partstat = part["long_syllable_statistics"]
                for stat in partstat.keys():
                    if(stat not in syllstat):
                        syllstat[stat] = list()
                        for a in range(len(partstat[stat])):
                            syllstat[stat].append(0)
                    for a in range(len(partstat[stat])):
                        syllstat[stat][a] += partstat[stat][a]
                part.pop("long_syllable_statistics")
            if("stressed_syllable_statistics" in part):
                partstat = part["stressed_syllable_statistics"]
                for stat in partstat.keys():
                    if(stat not in stressstat):
                        stressstat[stat] = list()
                        for a in range(len(partstat[stat])):
                            stressstat[stat].append(0)
                    for a in range(len(partstat[stat])):
                        stressstat[stat][a] += partstat[stat][a]
                part.pop("stressed_syllable_statistics")
            if("wordstat" in part):
                partstat = part["wordstat"]
                for stat in partstat.keys():
                    if(stat not in wordstat):
                        wordstat[stat] = 0
                    wordstat[stat] += partstat[stat]
                wordstat["_vocabulary"] = wordstat["_vocabulary"] / len(text["parts"])
                wordstat["_repetitivity"] = wordstat["_repetitivity"] / len(text["parts"])
                if(wordstat["_repetitivity"] == 0):
                    print("Ajaj! " + str(len(text["parts"])))
                part.pop("wordstat")
            if("number_of_stanzas" in part):
                stanzas += part["number_of_stanzas"]
                part.pop("number_of_stanzas")
            if("number_of_lines" in part):
                lines += part["number_of_lines"]
                part.pop("number_of_lines")
            if("number_of_words" in part):
                words += part["number_of_words"]
                part.pop("number_of_words")
    if(stanzas>0):
        text["number_of_stanzas"] = stanzas
    if(lines>0):
        text["number_of_lines"] = lines
    if(words>0):
        text["number_of_words"] = words
    if(len(syllstat)>0):
        text["long_syllable_statistics"] = syllstat
    if(len(stressstat)>0):
        text["stressed_syllable_statistics"] = stressstat
    if(len(wordstat)>0):
        text["wordstat"] = wordstat
    return(text)


def pdcdata(parameters, corpus):
    """ Fills a JSON-compatible corpus with metadata from the PDC system. """

    for text in corpus:
        poemid = text["poem_id"]
        poem = rep.searchm('poemid', [poemid])
        print(poemid, end='')
        if('date' in parameters):
            data = rep.show(['date'], poem)
            text["poem_date"] = json.loads(data[0][1][0])["date"]
        if('incipit' in parameters):
            text["poem_incipit"] = rep.show(['incipit'], poem)[0][1][0]
        if('sources' in parameters):
            text["poem_sources"] = rep.show(['sourcecat'], poem)[0][1]
            # print(text["sources"])
        if('genre' in parameters):
            text["poem_genre"] = rep.show(['genre'], poem)[0][1]
        if('metre' in parameters):
            text["poem_metre"] = json.loads(rep.show(['metre'], poem)[0][1][0])["metre"]
        if('acrostic' in parameters):
            text["poem_acrostic"] = json.loads(rep.show(['acrostic'], poem)[0][1][0])["acrostic"]
        if('colophon' in parameters):
            text["poem_colophon"] = json.loads(rep.show(['colophon'], poem)[0][1][0])["colophon"]
        if('place' in parameters):
            data = rep.show(['place'], poem)[0][1][0]
            if(len(data)>0):
                text["poem_place"] = json.loads(data)["place"]
    return(corpus)
        


# def listmorph(morph, purelist):
#     """ Converts the output of emMorphOMH into a proper lemmatization using the Purepos output. """
#     morph = re.sub(r'\[EOL\].*\n', '', morph)
#     morph = re.sub(r'\n\n\n', '\n\n', morph)
#     morphlist = morph.split('\n\n')
#     outlist = []
#     for i in range(len(morphlist)):
#         pureentry = mconv(morphlist[i])
#         pureentry.split('\n')
#         # print(str(i) + '\t' + morphlist[i].split('\n')[0] + '\t' + purelist[i+1])
#         for j in range(len(pureentry)):
#             if(pureentry[j] == purelist[i+1]):
#                 outlist.append(morphlist[i].split('\n')[j])
#                 print(pureentry[j])
#     return outlist


def convert(text):
    """ Converts between the emMorphOMH and Purepos formats. """
    global unanalyzed
    global unanalyzed_freq
    global unanalyzed_pos
    word = text.split('\n\n')
    out = ''
    space = False
    wcount = 0
    unanalyzed_pos.clear()
    for w in word:
        if('[EOS]' in w): # EOS if every stanza is a sentence, EOL if every line is a sentence.
            out = out + '\n'
            space = False
        elif('[EOL]' not in w): # inverse! EOL if every stanza is a sentence, EOS if every line is a sentence.
            if(space == True):
                out += ' '
            else:
                space = True
            out += mconv(w)
            wcount += 1
        if('+?' in w and w[0:5] not in ['[EOL]', '[EOS]']):
            ua = re.sub(r'([^\t]+)\t.*', r'\1', w)
            unanalyzed.add(ua)
            unanalyzed_pos.append(wcount)
            if(ua in unanalyzed_freq):
                unanalyzed_freq[ua] += 1
            else:
                unanalyzed_freq[ua] = 1
    return out


def mconv(w):
    """ Converts one word of emMorphOMH output to Purepos input. """
    """ Még kell: összetett szavaknál a lemma legyen az összetétel. (kész)
    Képzett szavaknál a lemma legyen a képzett alak. """
    ppos = []
    orig = ''
    for row in w.split('\n'):
        column = row.split('\t')
        if(len(column)==3):
            orig = column[0]
            if('+?' in column[1]):
                chain = ''
            else:
                nounlist = re.findall('[A-Za-zűáéúőóüöíŰÁÉÚŐÓÜÖÍ]+\[[NQ]\]', column[1]) # List of noun (and quantitative) morphemes in the word
                # derivlist = re.findall('[A-Za-zűáéúőóüöíŰÁÉÚŐÓÜÖÍ]+\[_', column[1]) # List of derivational suffixes in the word
                if('[VPfx]' in column[1]):
                    vpfx = re.sub(r'(.*)(\[VPfx\])(?!.*\2)(.*)', r'\1', column[1]) # Everything before the last [VPfx] tag.
                    vpfx = re.sub(r'\[.*?\]', r'', vpfx) # Only the text without tags: this is the verbal prefix.
                    verb = re.sub(r'(.*)(\[VPfx\])(?!.*\2)(.*)', r'\3', column[1]).split('[')[0] # This is the radical of the verb.
                    chain = vpfx + verb # This is the verb with all the prefixes (like "el-kihirdet" in case of "el-kihirdetteték"): the lemma.
                    # chain = column[1].split('[VPfx]')[0] + column[1].split('[VPfx]')[1].split('[')[0] # This one could not handle multiple prefixes.
                elif(len(nounlist)>1):
                    chain = ''
                    for noun in nounlist:
                        chain += re.sub(r'([A-Za-zűáéúőóüöíŰÁÉÚŐÓÜÖÍ]+)\[[NQ]\]', r'\1', noun)
                else:
                    chain = column[1].split('[')[0] # The lemma is before the first bracket.
                # if(len(derivlist)>0): # The lemma has to contain the derivative suffixes.
                #     first = True
                #     if('[V]' in column[1] and chain[-2:] == 'ik'): # handling the so-called "ikes igék" problem
                #         chain = chain[0:-2]
                #     print(chain + ' -> ', end='')
                #     for morpheme in re.findall(r'[^\[\]]+\[[^\]]+\]', column[1]):
                #         mo = re.sub(r'([^\[\]]+)\[([^\]]+)\]', r'\1', morpheme)
                #         an = re.sub(r'([^\[\]]+)\[([^\]]+)\]', r'\2', morpheme)
                #         if(first == True):
                #             first = False
                #         else:
                #             if('Adj' not in an and 'Adv' not in an and '_' not in an and an not in ['N', 'Q', 'V']):
                #                 chain += mo
                #             else:
                #                 chain += mo
                #                 break
                #     print(chain)
                chaincat = re.findall(r'\[.*?\]', column[1]) # All the tags in one list.
                for cat in range(len(chaincat)):
                    chaincat[cat] = re.sub(r'\[(.*?)\]', '\\1', chaincat[cat]) # Clearing the brackets of the tags.
                chain = chain + '[' + ':'.join(chaincat) + ']' # The chain of morphological categories separated by :.
            ppos.append(chain)
    out = orig
    if(len(ppos)>0 and len(ppos[0])>0):
        out = out + '{{' + '||'.join(ppos) + '}}' # All the possible analyses separated with ||.
    return out


def linesearch(pattern, corpus):
    """ Searches for a pattern in the lines of a JSON-compatible corpus.
    Returns the number of hits. """
    """ Would be nice if I could give this function another function name as an argument, that it should call if there is a hit. """
    print("Searching for '" + pattern + "'.")
    hits = dict()
    hits["hits"] = 0
    hits["poems"] = dict()
    for poem in corpus:
        hitpoem = 0
        linelist = []
        if("parts" in poem):
            for part in poem["parts"]:
                for stanza in part["stanzas"]:
                    for line in stanza["lines"]:
                        if("line_text" in line):
                            hitline = len(re.findall(pattern, line["line_text"]))
                            if(hitline > 0):
                                linelist.append(line["line_text"])
                                hitpoem += hitline
        else:
            for stanza in poem["stanzas"]:
                for line in stanza["lines"]:
                    if("line_text" in line):
                        hitline = len(re.findall(pattern, line["line_text"]))
                        if(hitline > 0):
                            linelist.append(line["line_text"])
                            hitpoem += hitline
        hits["hits"] += hitpoem
        if(hitpoem > 0):
            print(poem["poem_id"] + ": " + str(hitpoem))
            hits["poems"][poem["poem_id"]] = linelist
            print('\n'.join(linelist))
    print("----------\nTotal hits: " + str(hits["hits"]) + '\n')
    return(hits)


def download_corpus(repertory, idlist):
    """ Downloads a list of poems from the PDC system.
    Returns a list of JSON-compatible poems."""
    download = repertory.show(['poemid','otkatxt','author','title', 'syllables'], idlist)
    corpus = []
    for poem in download:
        if(len(poem[2][0])>0):
            print(poem[1][0])
            jpoem = poemjson(poem[2][0], poem[1][0], poem[3][0], poem[4][0])
            corpus.append(jpoem)
    return corpus


def import_corpus(location):
    """ Loads a list of poems from a directory
    containing plain text files.
    Returns a list of JSON-compatible poems.
    Not yet ready at all."""
    corpus = []
    # f = os.listdir()
    onlyfiles = [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))==True]
    for poem in onlyfiles:
        file = open(location + '/' + poem, "r")
        if(poem[-4:] == '.txt'):
            title = poem[:-4]
        else:
            title = poem
        corpus.append(poemjson(file.read(), title, '', title))
        file.close()
    return corpus


def load_corpus(location):
    """ Loads a list of poems from a directory
    containing JSON files.
    Returns a list of JSON-compatible poems."""
    corpus = []
    # f = os.listdir()
    onlyfiles = [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))==True]
    for poem in onlyfiles:
        file = open(location + '/' + poem, "r")
        corpus.append(json.loads(file.read()))
        file.close()
    return corpus


def store_corpus(location, corpus):
    """ Writes a list of poems in JSON format
    to the specified directory. """
    if not os.path.exists(location):
        os.makedirs(location)
    for poem in corpus:
        jsp = json.dumps(poem, indent=2, ensure_ascii=False)
        # print(jsp)
        poemid = 'UNKNOWN'
        if('poem_id' in poem):
            poemid = poem["poem_id"]
        file = open(location + '/' + poemid + ".json", "w")
        file.write(jsp)
        file.close()


def analyze_corpus(analyze_list, corpus):
    errlist = set([])
    for poem in corpus:
        """ Different normalization rules for Tinódi and other authors. """
        author = ''
        title = ''
        poemid = ''
        if('poem_id' in poem):
            poemid = poem["poem_id"]
        if('poem_author' in poem):
            author = poem["poem_author"]
        if('poem_title' in poem):
            title = poem["poem_title"]
        if('Tinódi' in author):
            normalizator = 'tinodi'
        else:
            normalizator = 'historias'
        print(poemid + '\t' + author + '\t' + title)
        if("parts" in poem):
            for part in poem["parts"]:
                if('morphology' in analyze_list):
                    pan = analyze_morph(part, normalizator)
                    part = pan[0]
                    errlist.update(pan[1])
                if('syllables' in analyze_list):
                    pan = analyze_syll(part)
                    part = pan[0]
                if('length' in analyze_list):
                    pan = analyze_length(part)
                    part = pan[0]
                if('phonetic' in analyze_list):
                    pan = analyze_phonetic(part)
                    part = pan[0]
                if('wordstat' in analyze_list):
                    pan = analyze_wordstat(part)
                    part = pan[0]
            poem = sum_parts(poem)
                # if('demo' in analyze_list): # Calling the demo function for parts, watch out for the other call!
                #     dan = analyze_demo(part)
                #     part = dan[0]
        else:
            if('morphology' in analyze_list):
                pan = analyze_morph(poem, normalizator)
                poem = pan[0]
                errlist.update(pan[1])
            if('syllables' in analyze_list):
                pan = analyze_syll(poem)
                poem = pan[0]
            if('length' in analyze_list):
                pan = analyze_length(poem)
                poem = pan[0]
            if('phonetic' in analyze_list):
                pan = analyze_phonetic(poem)
                poem = pan[0]
            if('wordstat' in analyze_list):
                pan = analyze_wordstat(poem)
                poem = pan[0]
            # if('demo' in analyze_list): # Calling the demo function for poems.
            #     dan = analyze_demo(poem)
            #     poem = dan[0]
        # if('syllables' in analyze_list):
        #     if(11 in poem["long_syllable_statistics"]):
        #         for a in poem["long_syllable_statistics"][11]:
        #             print(a, end='\t')
        #         print('')
        # if('length' in analyze_list):
        #     print(str(poem["number_of_stanzas"]) + '\t' + str(poem["number_of_lines"]) + '\t' + str(poem["number_of_words"]))
        errfile = open("errors.csv", "w")
        for err in errlist:
            errfile.write(err + '\n')
        errfile.close()
    return corpus

def extract_text(corpus):
    """ Extracts the text of a corpus and returns it in a very simple format. """
    ctext = []
    for poem in corpus:
        text = ''
        print(poem["poem_id"])
        if("poem_author" in poem):
            author = poem["poem_author"]
        else:
            author = ''
        if("poem_incipit" in poem):
            incipit = poem["poem_incipit"]
        else:
            incipit = ''
        text += author + ": " + incipit + " (" + poem["poem_id"] + ")\n\n"
        if("parts" in poem):
            for part in poem["parts"]:
                for stanza in part["stanzas"]:
                    for line in stanza["lines"]:
                        if("line_text" in line):
                            text += line["line_text"] + '\n'
                    text += '\n'
        else:
            for stanza in poem["stanzas"]:
                for line in stanza["lines"]:
                    if("line_text" in line):
                        text += line["line_text"] + '\n'
                text += '\n'
        ctext.append(text)
    return(ctext)
