import argparse
import pickle

class getNets:
    def __init__(self, files):
        self.files = files
        self.player_nets = {}

    def run(self):
        for file in self.files:
            chats = pickle.load(open(file, "rb"))
            for chat in chats:
                if "added on" in chat:
                    player = chat.split(" ")[0]
                    amount = int(float(chat.split(" ")[3]) * 100)
                    self.update_player_net(player, -1 * amount)
                    print(chat, sum(self.player_nets.values()))
                if "stood up with" in chat:
                    player = chat.split(" ")[0]
                    amount = int(float(chat.split(" ")[4]) * 100)
                    self.update_player_net(player, amount)
                    print(chat, sum(self.player_nets.values()))


        for player in self.player_nets:
            self.player_nets[player] /= 100.0

        print(self.player_nets)
        total_net = sum(self.player_nets.values())
        print("Total net = {}".format(total_net))
        return self.player_nets

    def update_player_net(self, player, amount):
        if player not in self.player_nets:
            self.player_nets[player] = 0
        self.player_nets[player] += amount


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-files', nargs='*', help="Files to generate nets from")

    args = parser.parse_args()
    print(args)
    nets = getNets(args.files)
    nets.run()


