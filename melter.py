import streamlit as st
import pandas as pd
import re

st.set_page_config(page_icon="🫕", page_title="The Melter")

def _max_width_():
	max_width_str = f"max-width: 1800px;"
	st.markdown(
		f"""
	<style>
	.reportview-container .main .block-container{{
		{max_width_str}
	}}
	</style>
	""",
		unsafe_allow_html=True,
	)

st.image(
	"https://em-content.zobj.net/thumbs/240/apple/325/fondue_1fad5.png",
	width=100,
)

st.title("The Melter")

st.write("""
The Melter is designed to streamline the process of reshaping data from a wide format to a long format. It's useful for handling CSV files exported from Beauhurst.

**How it works:**
1. **Upload a CSV file:** Use the uploader widget to add your Beauhurst exported file.
2. **Select ID Column Names:** Choose columns that uniquely identify each row (e.g., URLs, company names).
3. **Select Variable Columns:** Choose the columns that you wish to transform from wide to long format (e.g., turnover, headcount).
4. **Transform and Download:** Click the button to transform the data and then download the reshaped CSV file.

Ensure your CSV file is correctly formatted for optimal performance. The Variable Columns should have unique sequential numbering, eg: 1,2,3 etc. If you encounter any issues, error messages will guide you through potential fixes.
""")


# Uses Streamlit's uploader widget to allow the user to upload a csv
uploaded_file = st.file_uploader("Upload a Beauhurst export file (CSV)",type='csv')


def column_rename(original_names):
	'''
	Renames the column names so there are no spaces and puts the sequential number in the export at the end
	'''
	new_names = original_names.copy()
	for i in range(len(new_names)):
		new_names[i] = new_names[i].replace(" (2007) ", "_")
		new_names[i] = new_names[i].replace("Head Office Address - Postcode (if UK)", "Head Office Address - Postcode (if UK)1")
		if bool(re.search(r'\d', new_names[i])) == True:
			digit_position = re.search(r"\d+", new_names[i]) # match one or more digits
			digit_str = new_names[i][digit_position.start():digit_position.end()].strip() # get full matched digit string
			new_names[i] = new_names[i].replace(digit_str, "")
			new_names[i] = new_names[i]+str(digit_str)
			new_names[i] = new_names[i].replace(" - ", "_")
			new_names[i] = new_names[i].replace(" ", "_")
			new_names[i] = new_names[i].replace("__", "_")
		else:
			new_names[i] = new_names[i].replace(" - ", "_")
			new_names[i] = new_names[i].replace(" ", "_")
	return new_names



def variable_rename(new_names):
	'''
	Creates versions of the columns names that would be suitable as stubs for the Pandas wide to long
	'''
	var_names = new_names.copy()
	for i in range(len(var_names)):
		var_names[i] = re.sub(r'[0-9]+', '', var_names[i])
	return set(var_names)


# If there is a csv, Streamlit shows it in an expandable dataframe
if uploaded_file is not None:
	file_container = st.expander("Check your uploaded CSV")
	shows = pd.read_csv(uploaded_file)
	uploaded_file.seek(0)
	file_container.write(shows)

	# Creates a dataframe from the uploaded file and creates a list of column names
	df = pd.read_csv(uploaded_file)

	# Check for completely blank columns
	blank_columns = df.columns[df.isna().all()].tolist()
	if blank_columns:
		st.warning(f"The following columns are completely blank and should be removed: {', '.join(blank_columns)}")

	# Check for completely blank rows
	blank_rows = df.index[df.isna().all(axis=1)].tolist()
	if blank_rows:
		st.warning(f"The following rows are completely blank and should be removed: {', '.join(map(str, blank_rows))}")

	original_names = list(df.columns.values)

	# Creating a list of column names for the user to choose from
	static_options = column_rename(original_names)

	# Creating lists of column names using Streamlit's multiselect input widget, remove id columns once selected
	static_column_names = st.multiselect("Please select the ID column names. This is information that you'd like associated with each row instance. Some likely choices are Beauhurst URL, company name, and Companies House ID.",static_options)
	variable_options = variable_rename([x for x in static_options if x not in static_column_names])
	variable_column_names = st.multiselect("Please select the variable you want to convert from wide to long format. This is data that is stored in several columns that you'd like as a unique row instance. Some likely choices are turnover, headcount, investor info, SIC code, and postcode.",variable_options)

	drop_empty_rows = st.radio(
	    "Drop rows with empty variable columns?",
	    ("Yes", "No"),
	    index=1
	)

	# Renaming the dataframe columns with the altered names so that it works in the wide_to_long
	column_dictionary = dict(zip(original_names, static_options))
	df = df.rename(columns=column_dictionary)

	# After the radio button for drop_empty_rows

	if st.button('Make the data long'):
		try:
			# First melt the dataframe
			id_vars = static_column_names
			value_vars = []
			
			# Get all columns that start with any of the variable_column_names
			for var in variable_column_names:
				value_vars.extend([col for col in df.columns if col.startswith(var)])
			
			# Melt the dataframe
			df_melted = pd.melt(df, 
							   id_vars=id_vars,
							   value_vars=value_vars,
							   var_name='variable')
			
			# Extract the base variable name and number
			df_melted['Number'] = df_melted['variable'].str.extract('(\d+)$')
			df_melted['variable'] = df_melted['variable'].str.replace('\d+$', '', regex=True)
			
			# Pivot the data to get the final format - using first() instead of mean
			df_new = df_melted.pivot_table(index=static_column_names + ['Number'],
										 columns='variable',
										 values='value',
										 aggfunc='first').reset_index()  # Changed from default mean to first
			
			if drop_empty_rows == "Yes":
				df_new = df_new.dropna(subset=variable_column_names)
			
			@st.cache_data
			def convert_df(df):
				return df.to_csv().encode('utf-8')

			csv = convert_df(df_new)

			st.download_button(
				label="Download data as CSV",
				data=csv,
				file_name='new_df.csv',
				mime='text/csv',
			)
		except ValueError as e:
			error_message = str(e)
			if "Length of passed values is x, index implies y" in error_message:
				st.error("Data Transformation Error: The number of selected columns does not match the expected format. Please review your column selections.")
			elif "cannot reindex from a duplicate axis" in error_message:
				st.error("Duplicate Column Error: There are duplicate columns in your selection. Please ensure each column is unique.")
			else:
				st.error(f"Unexpected Error: {error_message}. Please review your selections and try again. If the issue persists, contact Dan for assistance.")

	else:
		st.write('')

else:
	st.info(
		f"""
			👆 Just add a CSV, no need to alter the column names.
			"""
		)

	st.stop()
