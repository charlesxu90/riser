# cd riser

# Reject all
# python3 reject_all.py


# Enrich coding sequences, i.e. deplete noncoding sequences
nohup python3 riser.py --target noncoding --duration 1 2>&1 > riser_coding_enrich.log &


# Enrich noncoding sequences
# python3 riser.py -t noncoding -d 48

