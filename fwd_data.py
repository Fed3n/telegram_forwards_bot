import telegram

class fwdData:
    '''
    Class grouping a forwarded message object
    made of 3 telegram message objects and
    mixed statistics for the message
    '''
    counter = 0
    tot_counter = 0

    def __init__(self, fwdmsg, chmsg1, chmsg2):
        #forwarded message
        self.fwdmsg = fwdmsg
        #key message in channel
        self.chmsg1 = chmsg1
        #forward message in channel
        self.chmsg2 = chmsg2

    def counter_update(self):
        self.counter += 1
        self.tot_counter += 1

    def tot_counter_update(self):
        self.tot_counter += 1

    def stats(self):
        return f"fwd counter: {self.counter}\ntot counter: {self.tot_counter}"
