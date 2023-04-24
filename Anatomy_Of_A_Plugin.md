
`name` The value of name it what shows at the top of the main window which lets the user know what contest is currently loaded.

`cabrillo_name` The value shows up in the cabrillo file that is generated.

`mode` The value of this determines what band/mode indicators appear at the left of the main window.

`columns` is a list containing the column numbers of the columns you want to apear in the logging window.

`dupe_type` defines the type of dupe checking.

`init_contest()` is called by the main program to set up the interface.

`next_field` holds the value of the field to jump to when the user presses the space bar while in the callsign field.

## Some interface background

There are 5 text entry boxes on the main screen. These are paired with a text label above them. Each entry box and text label are held in a "field" container. The first field, we'll call field0 is always displayed. It contains the callsign entry. `field1` holds the RST sent. `field2` holds the RST received. `field3` and `field4` hold `other_1` and `other_2` The purpose of these varies with each contest.

`interface()` which is called as part of the init_contest, hides and shows the fields mentioned above. the `label.setText()` part changes the text label in field4 giving the user a hint what to type in there.

