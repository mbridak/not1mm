# <center>Multi Multi</center>

Work is underway on Multi Multi contest operations. There is a companion project [renfield](https://github.com/mbridak/renfield) that will be needed for this. The idea is to have a separate slave server running, preferably, on another computer that's on the same network as the contesting PC's. This server will handle all the database CRUD operations. It will also handle the functions of handing out serial numbers and checking of a contact is a dupe. In the end, generating a Cabrillo file.

![renfield](https://github.com/mbridak/renfield/raw/refs/heads/main/pic/renfield_cli.svg)

This is a very lightweight terminal application and can be easily hosted on a Raspberry Pi or similar device. In a pinch it can be run along side Not1MM on one of the contesting machines. Tho I'd think twick about that.

You could even use this while operating alone as an automated backup. So in case your logging computer should fail, you'd have a copy of the contest log.

In the configuration dialog under the group tab, select Connect to server.

![config](https://github.com/mbridak/not1mm/raw/master/pic/configuration_group.png)

One computer needs to be the master station. The master station will tell the renfield server what contest is being run.

For the settings of the contest, if the Operator is set to "MULTI-OP" and the Transmitter category is not "ONE" or "SWL" Not1MM will ask the renfield server for serial numbers and dupe checks.

![contest settings](https://github.com/mbridak/not1mm/raw/master/pic/multi_multi.png)

