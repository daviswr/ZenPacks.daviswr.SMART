#pylint: disable=invalid-name
""" Shared data for modeler & parser """

HEALTH_FAILED = 1
HEALTH_PASSED = 0
HEALTH_UNKNOWN = 2
SMART_DISABLED = 1
SMART_ENABLED = 0
SMART_UNKNOWN = 2

# https://en.wikipedia.org/wiki/S.M.A.R.T.
attr_override = {
    '1': 'Raw Read Error Rate',
    '2': 'Throughput Performance',
    '3': 'Spin Up Time',
    '4': 'Start Stop Count',
    '5': 'Reallocated Sector Ct',
    '7': 'Seek Error Rate',
    '8': 'Seek Time Performance',
    '9': 'Power On Hours',
    '10': 'Spin Retry Count',
    '11': 'Calibration Retry Count',
    '12': 'Power Cycle Count',
    '169': 'Remaining Life Percentage',
    '170': 'Available Reserved Space',
    '171': 'Program Fail Count',
    '172': 'Erase Fail Count',
    '173': 'Ave Block-Erase Count',
    '174': 'Unexpect Power Loss Ct',
    '175': 'Program Fail Count Chip',
    '176': 'Erase Fail Count Chip',
    '177': 'Wear Leveling Count',
    '178': 'Used Rsvd Blk Cnt Chip',
    '179': 'Used Rsvd Blk Cnt Tot',
    '180': 'Unused Rsvd Blk Cnt Tot',  # Unused Reserve NAND Blk
    '181': 'Program Fail Cnt Total',
    '182': 'Erase Fail Count Total',
    '183': 'Runtime Bad Block',        # SATA Interfac Downshift
    '184': 'End-to-End_Error',         # Error Correction Count
    '187': 'Uncorrectable Error Cnt',  # Reported Uncorrect
    '188': 'Command Timeout',
    '189': 'High Fly Writes',          # Airflow Temperature Cel
    '190': 'Airflow Temperature Cel',
    '191': 'G-Sense Error Rate',
    '192': 'Power-Off Retract Count',
    '193': 'Load Cycle Count',
    '194': 'Temperature Celsius',
    '195': 'Hardware ECC Recovered',
    '196': 'Reallocated Event Count',
    '197': 'Current Pending Sector',
    '198': 'Offline Uncorrectable',
    '199': 'CRC Error Count',          # UDMA CRC Error Count
    '200': 'Multi Zone Error Rate',
    '201': 'Unc Soft Read Err Rate',
    '202': 'Percent Lifetime Remain',
    '204': 'Soft ECC Correct Rate',
    '206': 'Write Error Rate',         # Flying Height
    '210': 'Success RAIN Recov Cnt',
    '225': 'Load/Unload Cycle Count',
    '230': 'Life Curve Status',
    '231': 'SSD Life Left',
    '235': 'POR Recovery Count',
    '240': 'Head Flying Hours',
    '241': 'Total LBAs Written',
    '242': 'Total LBAs Read',
    '246': 'Total LBAs Written',       # Total Host Sector Write
    '247': 'Host Program Page Count',
    '248': 'FTL Program Page Count',
    }

# *Not* exhaustive...
vendor_dict = {
    'CT': 'Crucial',
    'HU': 'Hitachi',
    'HUC': 'Hitachi',
    'KB': 'Kioxia',
    'KBG': 'Kioxia',
    'MK': 'Mushkin',
    'MKN': 'Mushkin',
    'SM': 'Samsung',
    'ST': 'Seagate',
    'TH': 'Toshiba',
    'THN': 'Toshiba',
    'WD': 'Western Digital',
    'WDC': 'Western Digital',
    'XP': 'Samsung',
    }
