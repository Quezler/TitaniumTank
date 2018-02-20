#MvM Pop File Highlighter utility
#
#Provides a user interface that allows custom syntax-highlighting of
#pop files and adding new/commonly used keywords to the highlighting list.
#
#WARNING: This program is ancient. No warranties are guaranteed by its functionality.
#What you see here is what you get - this will not receive any updates or maintenance.

"""
=============================================================================
Titanium Tank Notepad++ Pop File Syntax Highlighter Generator
Copyright (C) 2018 Potato's MvM Servers.  All rights reserved.
=============================================================================

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License, version 3.0, as published by the
Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""





#Imports
from tkinter import *
from tkinter.messagebox import showinfo, showerror, askyesno
from tkinter.colorchooser import askcolor
from tkinter.scrolledtext import ScrolledText

from xml.etree.ElementTree import fromstring, tostring
from xml.dom.minidom import parseString as parse_string



#Preferred preview font goes here:
PREVIEW_FONT = "Courier New" #"Consolas"





class potato(object):

#Draft the entire GUI window and load the old data in here:

    def __init__(self, win):

        #Hide the main window first. DO NOT USE IT!
        self.win = win
        win.withdraw()

        #Write 3 toplevel windows:
        #
        #- A previewer window
        #- A highlighter window
        #- A keywords listing window
        self.win1 = Toplevel(win, bg="#FFFFFF")
        self.win2 = Toplevel(win)
        self.win3 = Toplevel(win)

        #Set properties for all 3 windows:
        self.win1.title("Syntax Highlighter Preview")
        self.win1.geometry("+5+5")
        self.win1.resizable(width=False, height=False)

        self.win2.title("Syntax Highlighter Settings")
        self.win2.geometry("+985+5")
        self.win2.resizable(width=False, height=False)

        self.win3.title("Keywords List")
        self.win3.geometry("+985+5")
        self.win3.resizable(width=False, height=False)

        #Hide the keywords window for now:
        self.win3.withdraw()

        #Load the base plugin highlighter data:
        self.load_base_data()

        #Create the previewer window:
        self.generate_preview_window()

        #Create the control panel window:
        self.generate_control_panel_window()

        #Then create the keywords window:
        self.generate_keywords_window()





#This method loads the syntax highlighter XML into memory and also extracts out current
#color and keyword configurations:

    def load_base_data(self):

        #Open the file (current working directory) first and swallow it in:
        with open("Pop_File_Highlighter.xml", mode="r", encoding="UTF-8") as f:
            self.root = fromstring(f.read())

        #Find the keywords sections and the style sections:
        userlang = self.root.find("UserLang")
        keywords_list_element = userlang.find("KeywordLists")
        styles_element = userlang.find("Styles")

        #Dictionary of keywords XML section linking to the GUI sections:
        self.xml_gui_keyword_link = {"Keywords1":"keywords",
                                     "Keywords5":"attributes",
                                     "Keywords3":"classes",
                                     "Keywords4":"properties",
                                     "Keywords2":"commons",
                                     "Keywords6":"skill",
                                     "Keywords7":"bm_wr",
                                     "Keywords8":"inc",
                                    }


        #Dictionary of the font color XML section linking to the GUI sections:
        self.xml_gui_color_link =   {"KEYWORDS1":"keywords",
                                     "KEYWORDS5":"attributes",
                                     "KEYWORDS3":"classes",
                                     "KEYWORDS4":"properties",
                                     "KEYWORDS2":"commons",
                                     "COMMENTS":"comments",
                                     "LINE COMMENTS":"comments",
                                     "DELIMITERS1":"strings",
                                     "FOLDER IN CODE1":"delimiters",
                                     "KEYWORDS6":"skill",
                                     "KEYWORDS7":"bm_wr",
                                     "KEYWORDS8":"inc",
                                     "NUMBERS":"numbers",
                                    }


        #Write a dictionary that will store all the keywords organized by their keyword category (1-8)
        self.keywords_bank = dict()

        #Do the same thing for font color of various parts of the syntax:
        self.colors = dict()

        #Now load the keywords data with old keywords:
        for x in keywords_list_element:
            name = x.attrib["name"]
            if name in self.xml_gui_keyword_link:
                gui_name = self.xml_gui_keyword_link[name]
                self.keywords_bank[gui_name] = x.text.split() if x.text is not None else list()

        #Also load the original color table:
        for x in styles_element:
            name = x.attrib["name"]
            if name in self.xml_gui_color_link:
                gui_name = self.xml_gui_color_link[name]
                font_color = "#{}".format(x.attrib["fgColor"])
                self.colors[gui_name] = font_color



                

#This method will generate a window where users can add keywords
#that should be highlighted under each category.
#
#Tkinter scrollbar text widget help:
#http://stackoverflow.com/questions/16577718/fit-tkinter-scrollbar-to-text-widget


    def generate_keywords_window(self):

        #Write a label first:
        self.message = 'In the textbox below, write each keyword on its OWN LINE for the category \"{}\".'
        self.message_label = Label(self.win3, text=self.message)
        self.message_label.grid(row=0, column=0, padx=10, pady=5)

        #Write a textbox:
        self.keywords_textbox = ScrolledText(self.win3, wrap=WORD, width=60, height=30, font=(PREVIEW_FONT, "12"))
        self.keywords_textbox.grid(row=1, column=0, padx=10, pady=5)

        #Write a button to return to the previous window:
        Button1 = Button(self.win3, text="Return to Control Panel", command=self.save_keywords)
        Button1.grid(row=2, column=0, padx=10, pady=5)





#This method saves the keywords data in the giant textbox into the keywords bank dictionary:

    def save_keywords(self):

        #Hide the keywords GUI window:
        self.win3.withdraw()

        #Grab the contents of the textbox:
        keywords_string = self.keywords_textbox.get(0.0, END)

        #Split it along newlines and then sort it:
        unique_keywords = {x.strip() for x in keywords_string.split("\n") if x.strip() != str()}
        keywords = sorted(unique_keywords, key=str.lower)

        #Insert it into the bank dictionary:        
        self.keywords_bank[self.keywords_category_active] = keywords

        #And display the control panel window:
        self.win2.deiconify()

        #Turn off the active window boolean:
        self.selection_active = False





#This method will generate the control panel window section:

    def generate_control_panel_window(self):

        #Grid in a label first:
        Label1 = Label(self.win2, text="In the window below, pick the colors that you want certain text to be highlighted in.")
        Label1.grid(row=0, column=0, padx=10, pady=5, columnspan=3)

        #Write 11 labels first:
        Label2 = Label(self.win2, text="Keywords:")
        Label3 = Label(self.win2, text="Properties:")
        Label4 = Label(self.win2, text="Classes:")
        Label5 = Label(self.win2, text="Skill:")
        Label6 = Label(self.win2, text="Attributes:")
        Label7 = Label(self.win2, text="Behavior Modifiers:")
        Label8 = Label(self.win2, text="Common Names:")
        Label9 = Label(self.win2, text="Weapon Restrictions:")
        Label10 = Label(self.win2, text="Comments:")
        Label11 = Label(self.win2, text="Strings:")
        Label12 = Label(self.win2, text="Numbers:")
        Label13 = Label(self.win2, text="Braces:")

        #Grid them in:
        Label2.grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Label3.grid(row=2, column=0, padx=10, pady=5, sticky=W)
        Label4.grid(row=3, column=0, padx=10, pady=5, sticky=W)
        Label5.grid(row=4, column=0, padx=10, pady=5, sticky=W)
        Label6.grid(row=5, column=0, padx=10, pady=5, sticky=W)
        Label7.grid(row=6, column=0, padx=10, pady=5, sticky=W)
        Label8.grid(row=7, column=0, padx=10, pady=5, sticky=W)
        Label9.grid(row=8, column=0, padx=10, pady=5, sticky=W)
        Label10.grid(row=9, column=0, padx=10, pady=5, sticky=W)
        Label11.grid(row=10, column=0, padx=10, pady=5, sticky=W)
        Label12.grid(row=11, column=0, padx=10, pady=5, sticky=W)
        Label13.grid(row=12, column=0, padx=10, pady=5, sticky=W)


        #Append all of them into the grouped lists:
        self.main_keywords.append(Label2)
        self.property_names.append(Label3)
        self.robot_classes.append(Label4)
        self.skill_level.append(Label5)
        self.attribute_names.append(Label6)
        self.weapon_restrictions.append(Label7)
        self.common_words.append(Label8)
        self.inc.append(Label9)
        self.comments.append(Label10)
        self.strings.append(Label11)
        self.numbers.append(Label12)
        self.delimiters.append(Label13)


        #Now grid in buttons that binds each to the colorpicker and to the keywords displayer.
        #The keywords displayer is to appear for only those that support special words (not symbols):
        types = ("keywords", "properties", "classes", "skill", "attributes", "bm_wr",
                 "commons", "inc", "comments", "strings", "numbers", "delimiters")

        has_keywords = set(self.xml_gui_keyword_link.values())

        for (x,y) in enumerate(types, start=1):
            Button1 = Button(self.win2, text="Select a color...", command=self.generate_button_func1(y))
            Button1.grid(row=x, column=1, padx=10, pady=5, sticky=W)

            if y in has_keywords:
                Button2 = Button(self.win2, text="Edit Keywords...", command=self.generate_button_func2(y))
                Button2.grid(row=x, column=2, padx=10, pady=5, sticky=W)


        #Now write dictionaries that store really important data.
        #When we rewrite the XML file back to the disk with the user's new data,
        #we will reference these dictionaries big time:
        self.dict_lists = {"keywords":self.main_keywords,
                           "attributes":self.attribute_names,
                           "classes":self.robot_classes,
                           "properties":self.property_names,
                           "skill":self.skill_level,
                           "bm_wr":self.weapon_restrictions,
                           "inc":self.inc,
                           "commons":self.common_words,
                           "comments":self.comments,
                           "strings":self.strings,
                           "numbers":self.numbers,
                           "delimiters":self.delimiters
                           }


        self.proper_keyword_names = {"keywords":"Keywords",
                                     "attributes":"Attributes",
                                     "classes":"Classes",
                                     "properties":"Properties",
                                     "skill":"Skill",
                                     "bm_wr":"Weapon Restrictions/Behavior Modifiers",
                                     "inc":"base",
                                     "commons":"Common Names",
                                     "comments":"Comments",
                                     "strings":"Strings",
                                     "numbers":"Numbers",
                                     "delimiters":"Braces"}


        #Bind the labels on the GUI to the color picker and the keywords updater:
        for (x,y) in self.dict_lists.items():
            for z in y:

                #Bind M1 to the color picker, bind M2 only if it's a keyword category.
                z.bind("<Button-1>", self.generate_button_func3(x))        #Left click = color picker
                if x in has_keywords:
                    z.bind("<Button-3>", self.generate_button_func4(x))        #Right click = keywords list

                #In addition, color-code in the previewer window in the color assigned to this label:
                z.config(fg=self.colors[x])


        #Write a boolean that dictates if a window is already active.
        #This prevents spamming up multiple windows from the previewer:
        self.selection_active = False

        #At the very bottom of the GUI, write 3 buttons:
        #- One to exit without saving our data
        #- One to exit with the new data
        Label13 = Label(self.win2, text="Click on the left button to exit without saving, the right button to save and exit.")
        Button3 = Button(self.win2, text="Exit without saving", command=self.exit_no_save)
        Button4 = Button(self.win2, text="Save new preferences", command=self.save_and_exit)

        i = len(types)+1
        Label13.grid(row=i, column=0, padx=10, pady=5, columnspan=3)
        Button3.grid(row=i+1, column=0, padx=10, pady=5)
        Button4.grid(row=i+1, column=2, padx=10, pady=5)
        




#Exits the program with no changes saved:

    def exit_no_save(self):

        #Confirm if we want to exit:
        if not askyesno("Exit Program?", "Are you sure you want to exit without saving your changes?"):
            return None

        #Then kill the mainloop, which will also kill all the child windows:
        self.win.destroy()





#Saves all of our changes to an XML file:

    def save_and_exit(self):

        #Find the keywords sections and the style sections (again):
        userlang = self.root.find("UserLang")
        keywords_list_element = userlang.find("KeywordLists")
        styles_element = userlang.find("Styles")

        #This time, preload the XML elements with NEW data!

        #Insert the keywords data with the new keywords:
        for x in keywords_list_element:
            name = x.attrib["name"]
            if name in self.xml_gui_keyword_link:
                gui_name = self.xml_gui_keyword_link[name]
                keywords = self.keywords_bank[gui_name]
                x.text = None if len(keywords) == 0 else " ".join(keywords)

        #Also insert the new color table:
        for x in styles_element:
            name = x.attrib["name"]
            if name in self.xml_gui_color_link:
                gui_name = self.xml_gui_color_link[name]
                font_color = self.colors[gui_name].replace("#", "").upper()
                x.attrib["fgColor"] = font_color


        #Pretty print the XML, and then save it to disk:
        pretty_printed = "\n".join([x for x in parse_string(tostring(self.root)).toprettyxml().split("\n") if x.strip() != str() and not x.startswith("<?xml")])

        with open("Pop_File_Highlighter.xml", mode="w", encoding="UTF-8") as f:
            f.write(pretty_printed)

        #Notify the user that the operation has been completed:
        showinfo("Success!", "Successfully saved new syntax preferences data! Go to Notepad++, then to Language > Define your language..., click on the Import button at the top, import the XML file (Pop_File_Highlighter.xml), restart Notepad++, open a .pop file, pick \"mvm_popfile\" as your language, and your settings should be in effect!")

        #Then terminate:
        self.win.destroy()
        return None





#These two methods generate a function that is bound to the buttons on the control panel and on
#the labels on the highlighter preview:

    generate_button_func1 = lambda self, x: lambda: self.update_colors(x)
    generate_button_func2 = lambda self, x: lambda: self.update_keywords(x)

    generate_button_func3 = lambda self, x: lambda *args: self.update_colors(x)
    generate_button_func4 = lambda self, x: lambda *args: self.update_keywords(x)





#When the color picker function is called, save the color choice to the dictionary and update
#all the labels with those colors:

    def update_colors(self, key):

        #If a window is already active, bail out:
        if self.selection_active:
            return None

        #Turn on the active window flag to prevent having duplicate windows from showing up:
        self.selection_active = True

        #Hide the second window (options window):
        self.win2.withdraw()

        #Grab the old color first:
        old_color = self.colors[key]

        #Ask the user for a color:
        (tuple_value, hexvalue) = askcolor(old_color)

        #If the exit value is None, toggle windows and bail out:
        if hexvalue is None:
            self.win2.deiconify()
            self.selection_active = False
            return None

        #Otherwise, update with the new color:
        self.colors[key] = hexvalue

        #And update ALL the labels on the GUI with this color:
        for x in self.dict_lists[key]:
            x.config(fg=hexvalue)

        #Then bring back the options window:
        self.win2.deiconify()
        self.selection_active = False





#When the keywords updater function is called, display a GUI window with all the keywords associated
#with that section:

    def update_keywords(self, key):

        #If a window is already active, bail out:
        if self.selection_active:
            return None

        #Turn on the active window flag to prevent having duplicate windows from showing up:
        self.selection_active = True

        #Hide the options window:
        self.win2.withdraw()

        #Grab the current preferred text color for these keywords/symbols:
        preferred_color = self.colors[key]

        #Make that the font color on the textbox:
        self.keywords_textbox.config(fg=preferred_color)

        #Fix the header label:
        self.message_label.config(text=self.message.format(self.proper_keyword_names[key]))

        #Grab the list of keywords from the keywords bank list, and then sort them:
        keywords = self.keywords_bank[key]
        keywords.sort(key=str.lower)

        #Join them into one giant string along a newline:
        giant_string = "\n".join(keywords)

        #Insert it into the textbox.
        #http://stackoverflow.com/questions/5322027/how-to-erase-everything-from-the-tkinter-text-widget

        #First, empty out the textbox:
        self.keywords_textbox.delete(0.0, END)

        #Then insert in the new text:
        self.keywords_textbox.insert(0.0, giant_string)

        #In an object variable, cache the category name:
        self.keywords_category_active = key

        #And display the window:        
        self.win3.deiconify()





#This method generates the previewer window:

    def generate_preview_window(self):
        
        #Write 14 frames that will hold 14 lines of code:
        Frame1 = Frame(self.win1)
        Frame2 = Frame(self.win1)
        Frame3 = Frame(self.win1)
        Frame4 = Frame(self.win1)
        Frame5 = Frame(self.win1)
        Frame6 = Frame(self.win1)
        Frame7 = Frame(self.win1, bg="#FFFFFF")
        Frame8 = Frame(self.win1)
        Frame9 = Frame(self.win1, bg="#FFFFFF")
        Frame10 = Frame(self.win1, bg="#FFFFFF")
        Frame11 = Frame(self.win1, bg="#FFFFFF")
        Frame12 = Frame(self.win1, bg="#FFFFFF")
        Frame13 = Frame(self.win1)

        #In the previewer window, start gridding in sample code:
        Label1 = self.write_label(Frame1, "#base")
        Label2 = self.write_label(Frame1, "robots_giant.pop")

        Label3 = self.write_label(self.win1, "WaveSchedule")
        Label4 = self.write_label(self.win1, "{")
        Label5 = self.write_label(self.win1, "    Templates")
        Label6 = self.write_label(self.win1, "    {")
        Label7 = self.write_label(self.win1, "        T_TFBot_Giant_Scout")
        Label8 = self.write_label(self.win1, "        {")

        Label9 = self.write_label(Frame2, "            Class")        
        Label10 = self.write_label(Frame2, "Scout")

        Label11 = self.write_label(Frame3, "            Skill")        
        Label12 = self.write_label(Frame3, "Expert")

        Label13 = self.write_label(Frame4, "            Attributes")        
        Label14 = self.write_label(Frame4, "Miniboss")

        Label15 = self.write_label(Frame5, "            WeaponRestrictions")        
        Label16 = self.write_label(Frame5, "MeleeOnly")

        Label17 = self.write_label(Frame6, "            Item")
        Label18 = self.write_label(Frame6, '"Festive Scattergun 2011"')

        Label19 = self.write_label(self.win1, "            CharacterAttributes")
        Label20 = self.write_label(self.win1, "            {")

        Label21 = self.write_label(Frame7, "                \"move speed bonus\"")
        Label22 = self.write_label(Frame7, "  3")
        Label23 = self.write_label(Frame7, "    // +200% move speed bonus")

        Label24 = self.write_label(self.win1, "            }")
        Label25 = self.write_label(self.win1, "        }")
        Label26 = self.write_label(self.win1, "    }")


        Label27 = self.write_label(self.win1, "    Wave")
        Label28 = self.write_label(self.win1, "    {")


        Label29 = self.write_label(self.win1, "        StartWaveOutput")
        Label30 = self.write_label(self.win1, "        {")

        Label31 = self.write_label(Frame8, "            Target")
        Label32 = self.write_label(Frame8, "wave_start_relay")

        Label33 = self.write_label(Frame9, "            Action")
        Label34 = self.write_label(Frame9, "Trigger")

        Label35 = self.write_label(self.win1, "        }")
        Label36 = self.write_label(self.win1, "        WaveSpawn")
        Label37 = self.write_label(self.win1, "        {")

        Label38 = self.write_label(Frame10, "            Where")
        Label39 = self.write_label(Frame10, "spawnbot")

        Label40 = self.write_label(Frame11, "            TotalCount")
        Label41 = self.write_label(Frame11, "10")

        Label42 = self.write_label(Frame12, "            MaxActive")
        Label43 = self.write_label(Frame12, "3")

        Label44 = self.write_label(self.win1, "            TFBot")
        Label45 = self.write_label(self.win1, "            {")

        Label46 = self.write_label(Frame13, "                Template")
        Label47 = self.write_label(Frame13, "T_TFBot_Giant_Scout")

        Label48 = self.write_label(self.win1, "            }")
        Label49 = self.write_label(self.win1, "        }")
        Label50 = self.write_label(self.win1, "    }")
        Label51 = self.write_label(self.win1, "}")


        #Grid them in correctly:
        #
        #Help that allows one-sided padding:
        #http://stackoverflow.com/questions/4174575/adding-padding-to-a-tkinter-widget-only-on-one-side

        #Base
        Label1.grid(row=0, column=0, sticky=W)
        Label2.grid(row=0, column=1, sticky=W)
        Frame1.grid(row=0, sticky=W)

        #WaveSchedule, braces, Templates, braces, template name
        Label3.grid(row=1, column=0, sticky=W)
        Label4.grid(row=2, column=0, sticky=W)
        Label5.grid(row=3, column=0, sticky=W)
        Label6.grid(row=4, column=0, sticky=W)
        Label7.grid(row=5, column=0, sticky=W)
        Label8.grid(row=6, column=0, sticky=W)

        #Class
        Label9.grid(row=0, column=0, sticky=W)
        Label10.grid(row=0, column=1, sticky=W)
        Frame2.grid(row=7, sticky=W)

        #Skill
        Label11.grid(row=0, column=0, sticky=W)
        Label12.grid(row=0, column=1, sticky=W)
        Frame3.grid(row=8, sticky=W)

        #Attributes
        Label13.grid(row=0, column=0, sticky=W)
        Label14.grid(row=0, column=1, sticky=W)
        Frame4.grid(row=9, sticky=W)

        #Weapon Restrictions
        Label15.grid(row=0, column=0, sticky=W)
        Label16.grid(row=0, column=1, sticky=W)
        Frame5.grid(row=10, sticky=W)

        #Item
        Label17.grid(row=0, column=0, sticky=W)
        Label18.grid(row=0, column=1, sticky=W)
        Frame6.grid(row=11, sticky=W)

        #CharacterAttributes + brace
        Label19.grid(row=12, column=0, sticky=W)
        Label20.grid(row=13, column=0, sticky=W)

        #Move speed bonus + comment
        Label21.grid(row=0, column=0, sticky=W)
        Label22.grid(row=0, column=1, sticky=W)
        Label23.grid(row=0, column=2, sticky=W)
        Frame7.grid(row=14, column=0, sticky=W)

        #Braces, Wave, StartWaveOutput
        Label24.grid(row=15, column=0, sticky=W)
        Label25.grid(row=16, column=0, sticky=W)
        Label26.grid(row=17, column=0, sticky=W)
        Label27.grid(row=18, column=0, sticky=W)
        Label28.grid(row=19, column=0, sticky=W)
        Label29.grid(row=20, column=0, sticky=W)
        Label30.grid(row=21, column=0, sticky=W)

        #Target wave_start_relay
        Label31.grid(row=0, column=0, sticky=W)
        Label32.grid(row=0, column=1, sticky=W)
        Frame8.grid(row=22, column=0, sticky=W)

        #Action Trigger
        Label33.grid(row=0, column=0, sticky=W)
        Label34.grid(row=0, column=1, sticky=W)
        Frame9.grid(row=23, column=0, sticky=W)

        #Braces, WaveSpawn
        Label35.grid(row=24, column=0, sticky=W)
        Label36.grid(row=25, column=0, sticky=W)
        Label37.grid(row=26, column=0, sticky=W)

        #Where
        Label38.grid(row=0, column=0, sticky=W)
        Label39.grid(row=0, column=1, sticky=W)
        Frame10.grid(row=27, column=0, sticky=W)

        Label40.grid(row=0, column=0, sticky=W)
        Label41.grid(row=0, column=1, sticky=W)
        Frame11.grid(row=28, column=0, sticky=W)

        Label42.grid(row=0, column=0, sticky=W)
        Label43.grid(row=0, column=1, sticky=W)
        Frame12.grid(row=29, column=0, sticky=W)

        #TFBot
        Label44.grid(row=30, column=0, sticky=W)
        Label45.grid(row=31, column=0, sticky=W)

        #Template
        Label46.grid(row=0, column=0, sticky=W)
        Label47.grid(row=0, column=1, sticky=W)
        Frame13.grid(row=32, column=0, sticky=W)

        #Braces
        Label48.grid(row=33, column=0, sticky=W)
        Label49.grid(row=34, column=0, sticky=W)
        Label50.grid(row=35, column=0, sticky=W)
        Label51.grid(row=36, column=0, sticky=W)

        #Notepad++ has 8 keyword categories.
        #So far we will have:
        #- Main Keywords (WaveSchedule, Wave, WaveSpawn, etc)
        #- Property Names (Class, Skill, Attributes, Where, TotalCount, etc)
        #- Robot Classes (Scout, Soldier, Pyro, etc)
        #- Skill Level (Easy, Normal, Hard, Expert)
        #- Attribute Names (AlwaysCrit, UseBossHealthBar, etc)
        #- Weapon Restrictions/Behavior Modifiers
        #- General words like T_TFBot, spawn (for spawnbot, etc), wave_ (for relays), robots_ (for #base statements)
        #- #base

        #Write lists that contain labels that have those 8 keyword categories in them:
        self.main_keywords = [Label3, Label5, Label19, Label27, Label29, Label36, Label44]
        self.property_names = [Label1, Label9, Label11, Label13, Label15, Label17, Label31,
                               Label33, Label38, Label40, Label42, Label46]
        self.robot_classes = [Label10]
        self.skill_level = [Label12]
        self.attribute_names = [Label14]
        self.weapon_restrictions = [Label16,]
        self.common_words = [Label2, Label7, Label32, Label34, Label39, Label47]
        self.inc = [Label16]
        

        #Fill in comments, strings, delimiters, and numbers here:
        self.comments =         [Label23]
        self.strings =          [Label18, Label21]
        self.numbers =          [Label22, Label41, Label43]
        self.delimiters =       [Label4, Label6, Label8, Label20, Label24, Label25, Label26,
                                 Label28, Label30, Label48, Label49, Label50, Label51,
                                 Label35, Label37, Label45]





#Helper method that grids labels onto the previewer GUI window:

    write_label = lambda self, master, text: Label(master, text=text, bg="#FFFFFF", font=(PREVIEW_FONT, "12"))    





#Start the program:
if __name__ == "__main__":
    win = Tk()
    app = potato(win)
    win.mainloop()
