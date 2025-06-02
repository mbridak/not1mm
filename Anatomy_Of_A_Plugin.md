# Contents of a plugin

This file gives a brief overview of the methods/functions in a plugin. If you are attempting to create your own plugin, this guide will give you a headstart.

## Variables that define the contest

`name` appears at the top of the main window to indicate what contest is currently loaded.

`cabrillo_name` shows up in the generated cabrillo file.

`mode` specifies what band/mode indicators appear on the left side of the main window.

`columns` is a list of the column numbers that are displayed in the logging window.

`dupe_type` defines the type of duplicate QSO checking.

`init_contest()` is called by the main program to setup the user interface.

`next_field`  specifies the field to jump to when the user presses the space bar while in the callsign field.

`self.contact.get("Call", "")` holds the contacts callsign.

There can be up to 5 text entry boxes on the main screen. These are paired with a text label above them. Each entry box and text label are held in a field container. The first field named `field0` holds the callsign and is always displayed. `Sent RST` is in `field1` and `Received RST` is in `field2`. There are two free variables `field3` and `field4` that hold `other_1` and `other_2`. These are specified to meet the individual exchange requirements of the various contests.

## The functions or methods

`interface()` is called by `init_contest`. It hides or shows the fields described above. The parameter `label.setText()` defines the text labels for `field3` or `field4`. The label text is chosen to guide user entry.

`set_tab_next()` and `set_tab_prev()` fill a dictionary object to define the forward and reverse TAB sequence. Not all text entry fields will be visible depending on the selected contest.

`set_contact_vars()` is called when the user presses ENTER which copies QSO data into the database. Multiplier and duplicate contact logic is implemented here.

`predupe()` is called once the user leaves the callsign entry field. The CWT plugin uses this to query the DB for a matching callsign allowing it to automatically populate the contact Name and CWOp #/State/DX fields.

`prefill()` is called as the user enters text in the callsign field and suggests possible matching callsigns in the database.

`points()` returns the point value of the logged contact. Point assigment is often complicated by continents, countries, zones, power, etc.

`show_mults()` returns the current multiplier count. This will be specific to each contest.

`show_qso()` returns the amount of valid contacts in the log.

`get_points()` returns the summed up values of the Points column.

`calc_score()` returns the current calculated score based on QSO points and mults.

`adif()` Generates an ADIF log in the user home directory.

`cabrillo()` Generates a Cabrillo file in the home directory using the Station and Contest settings. This file usually needs some manual editing.

`recalculate_mult()` This may be used to update the points/multiplier arithmetic when a logged contact is edited. 

## Retrieving contact station information

Often you may need to know if the contact station is located in particular country, continent, or other information for the purpose of scoring. You can get this information with the following code snippet.

```python
mycountry = ""
mycontinent = ""
mycqzone = ""
myituzone = ""
myprimary_pfx = ""

hiscountry = ""
hiscontinent = ""
hiscqzone = ""
hisituzone = ""
hisprimary_pfx = ""

result = self.cty_lookup(self.station.get("Call", ""))
if result is not None:
    item = result.get(next(iter(result)))
    mycountry = item.get("entity", "")
    mycontinent = item.get("continent", "")
    mycqzone = item.get("cq", "")
    myituzone = item.get("itu", "")
    myprimary_pfx = item.get("primary_pfx", "")


result = self.cty_lookup(self.contact.get("Call", ""))
if result is not None:
    item = result.get(next(iter(result)))
    hiscountry = item.get("entity", "")
    hiscontinent = item.get("continent", "")
    hiscqzone = item.get("cq", "")
    hisituzone = item.get("itu", "")
    hisprimary_pfx = item.get("primary_pfx", "")
```

## Making a new plugin by modifying an existing one

A straightforward way to create a new contest plugin is finding an existing plugin with the same or similar exchange and modifying it as necessary. [Here](./contest_exchanges.md) is a pretty good list of contests and their exchange types.

## Inserting a new contest so it appears in the dropdown list

Each contest plugin is linked to a corresponding entry in the contest dropdown list. To add a new contest into the list of available contests, the `new_contest.ui` XML file located in the Data directory must be manually edited. This can be illustrated with the following example using a snippet of the XML code for two sequential dropdown selections `REF SSB` and `STEW PERRY TOPBAND`:

```xml
     <item>
      <property name="text">
       <string>REF SSB</string>
      </property>
     </item>
     <item>
      <property name="text">
       <string>STEW PERRY TOPBAND</string>
      </property>
     </item>    
```

We wish to place a new entry called `SOME CONTEST NAME` between them. The XML file is modified using the `item` attribute as follows:

```xml
     <item>
      <property name="text">
       <string>REF SSB</string>
      </property>
     </item>
     <item>
      <property name="text">
       <string>SOME CONTEST NAME</string>
      </property>
     </item>
     <item>
      <property name="text">
       <string>STEW PERRY TOPBAND</string>
      </property>
     </item>
```

An entry for `SOME CONTEST NAME` will now appear in the dropdown list. When the user selects a contest on the list, the program will search for the corresponding plugin in the `plugins` directory. The capitalized text is converted to lowercase, any spaces are replaced with underscores, and a `.py` suffix is appended. In this example the corresponding contest plugin must be named `some_contest_name.py`

