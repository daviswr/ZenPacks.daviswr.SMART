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
    '171': 'SSD Program Fail Count',
    '172': 'SSD Erase Fail Count',
    '173': 'SSD Wear Leveling Count',
    '174': 'Unexpected Power Loss Count',
    '175': 'Program Fail Count Chip',
    '176': 'Erase Fail Count Chip',
    '177': 'Wear Leveling Count',
    '178': 'Used Rsvd Blk Cnt Chip',
    '179': 'Used Rsvd Blk Cnt Tot',
    '180': 'Unused Rsvd Blk Cnt Tot',
    '181': 'Program Fail Cnt Total',
    '182': 'Erase Fail Count Total',
    '183': 'Runtime Bad Block',
    '184': 'End-to-End Error',
    '187': 'Reported Uncorrect',
    '192': 'Power-Off Retract Count',
    '193': 'Load Cycle Count',
    '194': 'Temperature Celsius',
    '195': 'Hardware ECC Recovered',
    '196': 'Reallocated Event Count',
    '197': 'Current Pending Sector',
    '198': 'Offline Uncorrectable',
    '199': 'UDMA CRC Error Count',
    '200': 'Multi Zone Error Rate',
    '202': 'Data Address Mark Errors',
    '206': 'Flying Height',
    '231': 'SSD Life Left',
    '210': 'Vibration During Write',
    '240': 'Head Flying Hours',
    '241': 'Total LBAs Written',
    '242': 'Total LBAs Read',
    }

# *Not* exhaustive...
vendor_dict = {
    'CT': 'Crucial',
    'MK': 'Mushkin',
    'SM': 'Samsung',
    'TH': 'Toshiba',
    'WD': 'Western Digital',
    'WDC': 'Western Digital',
    'XP': 'Samsung',
    }
