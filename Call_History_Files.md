# Call History Files

To use Call History files, go to `FILE -> Configuration Settings`

![Config Screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_options.png)

Place a check in the `Use Call History` box. Call history files are very specific to the contest you are working. Example files can be obtained from [n1mm's](https://n1mmwp.hamdocs.com/mmfiles/categories/callhistory/?) website. They have a searchbox so you can find the contest you are looking for. If you are feeling masocistic, you can craft your own. The general makeup of the file is a header defining the fields to be used, followed by by lines of comma separated data.

## Creating your own Call History files

You can use [adif2callhistory](https://github.com/mbridak/adif2callhistory) to generate your own call history file from your ADIF files. You can use a [list of call history keys](https://github.com/mbridak/not1mm/blob/master/call_history_keys.md) used for each contest.

An example file excerpt looks like:

```text
!!Order!!,Call,Name,State,UserText,
#
# 0-This is helping file, LOG what is sent.
# 1-Last Edit,2024-08-18
# 2-Send any corrections direct to ve2fk@arrl.net
# 3-Updated from the log of Marsh/KA5M
# 4-Thanks Bjorn SM7IUN for his help. 
# 5-Thanks
# NAQPCW 
# NAQPRTTY 
# NAQPSSB 
# SPRINTCW 
# SPRINTLADD 
# SPRINTNS 
# SPRINTRTTY 
# SPRINTSSB
AA0AC,DAVE,MN,Example UserText
AA0AI,STEVE,IA,
AA0AO,TOM,MN,
AA0AW,DOUG,MN,
AA0BA,,TN,
AA0BR,,CO,
AA0BW,,MO,
```

The first line is the field definition header. The lines starting with a `#` are comments. Some of the comments are other contests that this file also works with.
This is followed by the actual data. If the matched call has `UserText` information, that user text is populated to the bottom left of the logging window.

So if one were to go to `FILE -> LOAD CALL HISTORY FILE` and choose a downloaded call history file for NAQP and typed in the call AA0AC while operating in the NAQP, after pressing space, one would see:

![Call History Example](https://github.com/mbridak/not1mm/raw/master/pic/call_history_example.png)

Where the Name and State would auto-populate and the UserText info apprears in the bottom left.