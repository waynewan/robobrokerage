import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
# --
import sys
import os 
import pandas
import numpy

# !!
# !! this is a bad idea, possible solution, 
# !! publish the library (oms) as a package 
# !!
__abspath = os.path.abspath(__file__)
__dirname = os.path.dirname(__abspath)
common_dir = f"{__dirname}/../../../../../common"
sys.path.append(f"{common_dir}/lib/quick_func")
print(common_dir)

# --
# !! some of the transformation might looks odd
# !! necessary to match robobrokerage.fidelity.get_history
# --
def get_history(csv_file_name):
	df0 = read_dirty_csv(csv_file_name,header_row=1,date_col=['Run Date','Settlement Date'], key_col=['Action','Symbol'])
	df1 = fidelity_dl_txn_formatter(df0)
	return df1

def fidelity_dl_txn_formatter(df0):
	df1 = df0.loc[:,['Action','Run Date','Symbol','Quantity','Price ($)','Amount ($)','Settlement Date','Action']]
	df1.columns = 'Type,Date,Symbol,Shares,Price,Amount,Settlement,Description'.split(',')
	# --
	type_val_map = {
		"YOU SOLD" : "SELL",
		"YOU BOUGHT" : "BUY", 
		"DIVIDEND RECEIVED" : "DIV",
		"ASSIGNED as" : "ASSIGNED",
		"REINVESTMENT FIDELITY" : "INT",
	}
	df1['Type'] = df1['Type'].str.split(" ").apply(lambda vv: type_val_map.get(" ".join(vv[0:2]),None) )
	df1.loc[df1['Type']=='DIV',["Shares","Price"]] = [ numpy.nan,numpy.nan ]
	# --
	df1 = df1[df1['Type'] !='INT']
	return df1

# --
# !! some of the transformation might looks odd
# !! necessary to match robobrokerage.fidelity.get_history
# --
def get_position(csv_file_name,account_code):
	df0 = read_dirty_csv(csv_file_name, header_row=0,
		num_col="Last Price,Last Price Change,Current Value,Today's Gain/Loss Dollar,Today's Gain/Loss Percent,Total Gain/Loss Dollar,Total Gain/Loss Percent,Percent Of Account,Cost Basis Total,Average Cost Basis".split(','),
		key_col=["Account Name"]
	)
	if(account_code is not None):
		df0 = df0[ df0['Account Number']==account_code ]
	df1 = fidelity_dl_pos_formatter(df0)
	return df1

def fidelity_dl_pos_formatter(df0):
	df1 = df0.loc[:,["Symbol","Description","Last Price","Current Value","Percent Of Account","Quantity","Cost Basis Total","Type"]]
	df1.columns = 'Symbol,Desc,Last Price,Current Value,% of Account,Quantity,Total Cost,Per Share'.split(',')
	df1['Per Share'] = df1['Total Cost'] / df1['Quantity']
	return df1

# --
# -- transaction file from fidelity contains header and footer
# --
def read_dirty_csv(filepath, header_row=1, date_col=[], num_col=[], key_col=[]):
	try:
		df = pandas.read_csv(
			filepath,
			engine='python',
			skip_blank_lines=True,
			header=header_row,
		)
		df.columns = df.columns.str.strip()
		for nnull in key_col:
			df = df[ ~ df[nnull].isna() ]
		for dcol in date_col:
			df[dcol] = pandas.to_datetime(df[dcol], errors='coerce')
		for ncol in num_col:
			try:
				df[ncol] = df[ncol].str.replace(r'[$%,]','',regex=True).astype(float)
			except Exception as e:
				print(ncol,e)
		return df
	except FileNotFoundError:
		print(f"Error: File not found at {filepath}")
		return pandas.DataFrame()
	except Exception as e:
		print(e)
		print(f"An error occurred during file reading: {e}")
		return pandas.DataFrame()

