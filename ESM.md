## ESM

ESM or Enter Sends Message. ESM is a feature in which the logging program will automatically
send the right function key macros based on the information present in the input fields and
which input field is active when you press the Enter key. You can see a common flow in the
examples below.

To test it out you can go to `FILE -> Configuration Settings`

![Config Screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_options.png)

Check the mark to Enable ESM and tell it which function keys do what. The keys will need
to have the same function in both Run and S&P modes. The function keys will highlight
green depending on the state of the input fields. The green keys will be sent if you
press the Enter key. You should use the Space bar to move to another field.

The contact will be automatically logged once all the needed info is collected and the
QRZ (for Run) or Exchange (for S&P) is sent.

### Run States

#### CQ

![CQ](https://github.com/mbridak/not1mm/raw/master/pic/esm_cq.png)

#### Call Entered send His Call and the Exchange

![Call Entered send His Call and the Exchange.](https://github.com/mbridak/not1mm/raw/master/pic/esm_withcall.png)

#### Empty exchange field send AGN till you get it

![Empty exchange field send AGN till you get it](https://github.com/mbridak/not1mm/raw/master/pic/esm_empty_exchange.png)

#### Exchange field filled, send TU QRZ and logs it

![Exchange field filled, send TU QRZ and logs it](https://github.com/mbridak/not1mm/raw/master/pic/esm_qrz.png)

### S&P States

#### With his call entered, Send your call

![With his call entered, Send your call](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_call.png)

#### If no exchange entered send AGN

![If no exchange entered send AGN](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_agn.png)

#### With exchange entered, send your exchange and log it

![With exchange entered, send your exchange and log it](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_logit.png)