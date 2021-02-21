#!/usr/bin/env python3

import argparse
import os
import os.path
import csv
import logging
import datetime

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Coinbase All Transactions File")
    parser.add_argument("-v", "--verbose", action='append_const', help="Control Verbosity", const=1, default=[])
    args = parser.parse_args()

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)

    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)

    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)

    elif VERBOSE > 2:
        logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger("manowar_server")

    logger.debug("Welcome to cccalc")

    if os.path.isfile(args.csv) is False:
        raise FileNotFoundError("Couldn't Find file : {}".format(args.csv))

    with open(args.csv) as all_txs_csv:

        tx_table = list()

        reader = csv.reader(all_txs_csv)

        past_headers = False

        for row in reader:

            logger.debug(len(row))

            if len(row) == 0:
                logger.debug("Ignoring Whitespace Row")
            elif past_headers is False and row[0] != "Timestamp":
                logger.debug("Ignoring Coinbase Header Row")
            elif past_headers is False:
                # This is the header Row
                past_headers = True
                my_headers = row[0:8]
            else:
                # This is a Data Row
                this_data = dict()

                for x in range(0, 8):
                    this_data[my_headers[x]] = row[x]

                tx_table.append(this_data)

        logger.debug(tx_table)
        cost_basis = dict(USDC={"running_cb": {"shares": 0,
                                               "avg_price": 1.0},
                                "sells": list()})

        for tx in tx_table:
            #
            asset_name = tx["Asset"]
            tx_type = tx["Transaction Type"]

            if asset_name not in cost_basis.keys():
                # Add cost_basis
                cost_basis[asset_name] = {"running_cb": {"shares": 0.00,
                                                          "avg_price": 0.00},
                                           "sells": list()}

            logger.debug(tx)
            now_cb = cost_basis[asset_name]["running_cb"]

            if tx_type not in ("Buy", "Sell", "Rewards Income", "Send", "Receive", "Convert", "Paid for an order"):
                logger.warning("Odd Type {}".format(tx_type))

            # External Spend Types "Send", "Recieve", "Paid for an order"
            if tx_type in ("Recieve"):
                # Assume same cost basis
                new_cb = {"shares": now_cb["shares"] + float(tx["Quantity Transacted"]),
                          "avg_price": now_cb["avg_price"]}
            elif tx_type in ("Recieve", "Paid for an order"):
                new_cb = {"shares": now_cb["shares"] - float(tx["Quantity Transacted"]),
                          "avg_price": now_cb["avg_price"]}
            # Buy Types (Modify CB Upwards) Buy, "Rewards Income"
            elif tx_type in ("Buy", "Rewards Income"):
                # Add to Cost Basis
                price_per = float(tx["USD Total (inclusive of fees)"]) / float(tx["Quantity Transacted"])
                new_cb = {"shares": now_cb["shares"] + float(tx["Quantity Transacted"]),
                          "avg_price": (now_cb["shares"] *
                                        now_cb["avg_price"] +
                                        float(tx["Quantity Transacted"]) *
                                        price_per)/(now_cb["shares"] +
                                                    float(tx["Quantity Transacted"]))
                          }

                cost_basis[asset_name]["running_cb"] = new_cb
            # Sell Types "Sell"
            elif tx_type in ("Sell", "Convert"):
                logger.info("Sell tx : {}".format(tx))

                sell_cost_basis = float(tx["Quantity Transacted"]) * now_cb["avg_price"]
                gain_loss = float(tx["USD Subtotal"]) - sell_cost_basis

                tx["sell_cost_basis"] = sell_cost_basis
                tx["gain_loss"] = gain_loss


                new_cb = {"shares": now_cb["shares"] - float(tx["Quantity Transacted"]),
                          "avg_price": now_cb["avg_price"]}

                if new_cb["shares"] < 0:
                    logger.warning("Odd New CB: {}")

                cost_basis[asset_name]["running_cb"] = new_cb
                cost_basis[asset_name]["sells"].append(tx)

                if tx_type == "Convert":
                    # If Convert Do the Update to USDC
                    logger.warning("Convert")
                    cost_basis["USDC"]["running_cb"]["shares"] + float(tx["USD Subtotal"])

        logger.info(cost_basis)

    all_sells = list()

    with open("cb_trans.csv", "w") as out_csv_fobj:
        for asset_name, asset_data in cost_basis.items():
            for this_sell in asset_data["sells"]:
                all_sells.append(this_sell)

        logger.warning(all_sells[0].keys())

        writer = csv.DictWriter(out_csv_fobj, fieldnames=all_sells[0].keys())

        writer.writeheader()

        for this_sell in all_sells:
            writer.writerow(this_sell)









