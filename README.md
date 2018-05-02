# adatip

Reddit tip bot for the Cardano ADA cryptocurrency.

Things:

Bot currently needs a local webserver for the www folder (I do python -m http.server) as this is how it accesses the bip39 english.txt and system reply json.

For the mtip module to work an account will need to be manually created and id's set up in config.

Bot uses the v0.2 wallet api for cardano-node, there is a v1 api but it is currently in beta and v0.2 is still supported.

There are a few hacks, like searching for the keyword "not enough money" in the error reply from the wallet api to recursively figure out the max amount that can be sent once the transaction fee is subtracted for an on chain transaction. 

The mtip off chain wallet database is extremely simple for the sake of... simplicity. However, this leaves no transaction record. Reddit comments never expire however, and even if the orginal user deletes their tip comment, the bot will have responded the tip amount. Since deposits and withdrawals are of course on chain, in the case of some catastrophic failure it is therefore technically possible to reconstruct the transaction history. Hourly backups are also made of the mtip and user databases.

The bot runs in big blocking process except for the deposit notification service so database conflicts shouldn't happen (the deposit notification service feeds into the main process for username lookup)
