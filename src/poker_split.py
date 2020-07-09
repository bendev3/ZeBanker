import argparse
import csv
import copy
import os
from site_reader import SiteReader
from datetime import datetime
from utils import log, val_to_float

WIN_LOSER_PAIRS = []

class PokerSplit:
    def __init__(self, files, nets=None):
        self.transactions = []
        self.nets = nets
        self.player_nets_dict = {}
        self.players_info_dict = {}
        self.files = files

    def run(self):
        if self.nets:
            self.player_nets_dict = self.nets
        else:
            self.get_player_info_from_csv(self.files)
        self.determine_payouts()
        self.test()
        return [self.print_nets(), self.print_payouts(), self.print_contact_info()]

    def print_nets(self):
        log("Printing results to string")
        winners = [player_tuple for player_tuple in self.player_nets_dict.items() if player_tuple[1] > 0]
        losers = [player_tuple for player_tuple in self.player_nets_dict.items() if player_tuple[1] < 0]
        tied = [player_tuple for player_tuple in self.player_nets_dict.items() if player_tuple[1] == 0]

        s = "*** Winners ***\n"
        for player_tuple in sorted(winners, key=lambda player_tuple: player_tuple[1], reverse=True):
            s += "{:<14}won ${:.2f}\n".format(player_tuple[0], player_tuple[1])

        for player_tuple in tied:
            s += "{:<14}broke even\n".format(player_tuple[0])

        s += "\n*** LOSERS ***\n"
        for player_tuple in sorted(losers, key=lambda player_tuple: player_tuple[1]):
            s += "{:<14}lost ${:.2f}\n".format(player_tuple[0], -1 * player_tuple[1])
        return s

    def print_payouts(self):
        s = "***  Payouts  ***\n"
        for transaction in self.transactions:
            s += "{:<14}{:<6}{:<13}${:.2f}\n".format(transaction[0], "--->", transaction[1], transaction[2])
        return s

    def print_contact_info(self):
        if len(self.players_info_dict) > 0:
            s = "*** Venmo Info ***\n"
            for player, venmo in self.players_info_dict.items():
                a = player + ": "
                if venmo:
                    s += "{:<14}{}\n".format(a, venmo)
            return s

    def determine_payouts(self):
        log("Determining payouts from previously read in csv(s)")
        player_nets_dict = copy.deepcopy(self.player_nets_dict)
        assert round(sum(player_nets_dict.values()), 10) == 0, "Sum: {}".format(sum(player_nets_dict.values()))

        player_nets_dict = self.check_for_zeros(player_nets_dict)
        player_nets_dict = self.check_for_cancellations(player_nets_dict)

        while len(player_nets_dict) > 0:
            if len(WIN_LOSER_PAIRS) > 0:
                win_loser_pair = WIN_LOSER_PAIRS.pop()
                winner = win_loser_pair[0], player_nets_dict[win_loser_pair[0]]
                loser = win_loser_pair[1], player_nets_dict[win_loser_pair[1]]
            else:
                winner = max(player_nets_dict.items(), key=lambda player_net_tuple: player_net_tuple[1])
                loser = min(player_nets_dict.items(),
                            key=lambda player_net_tuple: -1 * player_net_tuple[1] if player_net_tuple[1] < 0 else float(
                                'inf'))
            # loser = min(player_nets_dict.items(), key=lambda player_net_tuple: player_net_tuple[1])
            win_name = winner[0]
            lose_name = loser[0]
            win_amt = round(winner[1], 10)
            lose_amt = round(loser[1], 10)

            if abs(win_amt) > abs(lose_amt):
                self.transact(lose_name, win_name, -1 * lose_amt)
                del player_nets_dict[lose_name]
                player_nets_dict[win_name] = round(player_nets_dict[win_name] + lose_amt, 10)
            else:
                self.transact(lose_name, win_name, win_amt)
                del player_nets_dict[win_name]
                player_nets_dict[lose_name] = round(player_nets_dict[lose_name] + win_amt, 10)
            player_nets_dict = self.check_for_cancellations(player_nets_dict)

    def check_for_zeros(self, player_nets_dict):
        for player in list(player_nets_dict):
            net = player_nets_dict[player]
            if net == 0:
                del player_nets_dict[player]
        return player_nets_dict

    def check_for_cancellations(self, player_nets_dict):
        players_to_remove = []
        for i, (player1, net1) in enumerate(player_nets_dict.items()):
            for player2, net2 in list(player_nets_dict.items())[i:]:
                if net1 == -1 * net2 and player1 not in players_to_remove and player2 not in players_to_remove:
                    players_to_remove += [player1, player2]
                    if net1 < 0:
                        self.transact(player1, player2, -1 * net1)
                    else:
                        self.transact(player2, player1, net1)

        for player in players_to_remove:
            del player_nets_dict[player]
        return player_nets_dict

    def transact(self, from_name, to_name, amount):
        log("Storing transaction of from {} to {} of amount {}".format(from_name, to_name, amount), 2)
        self.transactions.append([from_name, to_name, amount])

    def get_player_info_from_csv(self, files):
        for file in files:
            log("Reading table info from file: {}".format(file))
            with open(file) as csvfile:
                reader = csv.reader(csvfile)
                next(csvfile)  # title
                next(csvfile)  # header
                for row in reader:
                    if len(row) >= 6 and "Hands played" not in row[0] and row[0] != '':
                        player_name = row[0]
                        net_at_this_table = round(val_to_float(row[3]) + val_to_float(row[4]), 10)
                        if player_name in self.player_nets_dict:
                            self.player_nets_dict[player_name] += net_at_this_table
                        else:
                            self.player_nets_dict[player_name] = net_at_this_table
                            venmo = row[5]
                            self.players_info_dict[player_name] = "@" + venmo.strip("@")

    def test(self):
        self._compare_transaction_net_to_net()
        self._check_transaction_sum()

    def _compare_transaction_net_to_net(self):
        log("Test to ensure the transactions sum up to net", 1)
        player_nets_dict_from_transactions = {}
        for [from_name, to_name, amount] in self.transactions:
            if from_name not in player_nets_dict_from_transactions:
                player_nets_dict_from_transactions[from_name] = 0
            if to_name not in player_nets_dict_from_transactions:
                player_nets_dict_from_transactions[to_name] = 0
            player_nets_dict_from_transactions[from_name] = round(player_nets_dict_from_transactions[from_name] - amount, 10)
            player_nets_dict_from_transactions[to_name] = round(player_nets_dict_from_transactions[to_name] + amount, 10)

        for player in player_nets_dict_from_transactions:
            transaction_net = round(player_nets_dict_from_transactions[player], 10)
            csv_net = round(self.player_nets_dict[player], 10)
            assert transaction_net == csv_net, \
                "{}, transaction net == csv net, {} == {}".format(player, transaction_net, csv_net)

    def _check_transaction_sum(self):
        log("Testing to ensure the sum of transactions amounts is half of the sum of the absolute values of the nets", 1)
        sum_of_transactions = round(sum([transaction[2] for transaction in self.transactions]), 10)
        sum_of_net_absolute_values = round(sum([abs(val) for val in self.player_nets_dict.values()]), 10)
        assert sum_of_transactions == sum_of_net_absolute_values / 2.0, "{} != {}".format(sum_of_transactions,
                                                                                          sum_of_net_absolute_values / 2.0)
