# Whats in a plugin

This file will give a brief overview as to what methods/functions are in a plugin. So if you are attempting to create your own plugin, you will have a headstart.

## Variables that define the contest

`name` The value of name it what shows at the top of the main window which lets the user know what contest is currently loaded.

`cabrillo_name` The value shows up in the cabrillo file that is generated.

`mode` The value of this determines what band/mode indicators appear at the left of the main window.

`columns` is a list containing the column numbers of the columns you want to apear in the logging window.

`dupe_type` defines the type of dupe checking.

`init_contest()` is called by the main program to set up the interface.

`next_field` holds the value of the field to jump to when the user presses the space bar while in the callsign field.

`self.contact.get("Call", "")` holds the contacts callsign.

## Some interface background

There are 5 text entry boxes on the main screen. These are paired with a text label above them. Each entry box and text label are held in a "field" container. The first field, we'll call `field0` is always displayed. It contains the callsign entry. `field1` holds the RST sent. `field2` holds the RST received. `field3` and `field4` hold `other_1` and `other_2` The purpose of these varies with each contest.

## The functions or methods

`interface()` which is called as part of the init_contest, hides and shows the fields mentioned above. the `label.setText()` part changes the text label in field3 or 4 giving the user a hint what to type in there.

`set_tab_next()` and `set_tab_prev()` fills a dictionary object with the order of text fields to TAB to. This can be important since all the text fields may not be visible for all contests.

`set_contact_vars()` is called when the user presses Enter. Information is copies from the interface to the contact object which will be stored in the DB. Here also is usually where the logic is that determins if a contact is a mult.

`predupe()` is called once the user leaves the callsign entry field. The CWT plugin uses this to look in the DB for the callsign to see if it can prefill the contact Name and CWOp #/State/DX fields from previous CWT contacts.

`prefill()` is called as the user enters text in the callsign field and there is enough characters to be a possible call.

`points()` returns the amount of points this current contact should be logged as. Often this can get complex as some contests base points on if a contact is in the same/different continent or country and the band/power the contacts occurred on.

`show_mults()` returns the current amount of multipliers. Each contest has it's own rules as to what constitutes a multiplier.

`show_qso()` returns the amount of valid contacts in the log.

`get_points()` Returns the summed up values of the Points column.

`calc_score()` Returns the current calculated score, often based on points and mults.

`adif()` Generates an ADIF log to the users home directory.

`cabrillo()` Generates a Cabrillo file, filling out the usual fields from Station and Contest settings. Usually needs to be tweaked for each contest.

`recalculate_mult()` Often if a contact is edited after it had been logged. It may change the contacts possible multiplier status. This method can be called from the main window to recalculate all of the logged contacts multiplier status.

## Getting Station and Contact Locations

Often you may need to know if a contact or the station is located in particular country or continent or other information for the purpose of scoring. You can get this information with the following code snippet.

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
if result:
    for item in result.items():
        mycountry = item[1].get("entity", "")
        mycontinent = item[1].get("continent", "")
        mycqzone = item[1].get("cq", "")
        myituzone = item[1].get("itu", "")
        myprimary_pfx = item[1].get("primary_pfx", "")


result = self.cty_lookup(self.contact.get("Call", ""))
if result:
    for item in result.items():
        hiscountry = item[1].get("entity", "")
        hiscontinent = item[1].get("continent", "")
        hiscqzone = item[1].get("cq", "")
        hisituzone = item[1].get("itu", "")
        hisprimary_pfx = item[1].get("primary_pfx", "")
```

## Making a new plugin by modifying an old one

A usually easy path to making a new contest plugin is finding an existing plug in for another contest that has the same exchange, then modifying it for the points and multipliers. [here](./contest_exchanges.md) is a pretty good list or contests and their exchange types.