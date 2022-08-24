import streamlit as st
import pandas as pd
import re
# test
###############################

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

st.set_page_config(page_icon="🫕", page_title="The Melter")

st.image(
	"https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/apple/325/fondue_1fad5.png",
	width=100,
)

st.title("The Melter")

###############################

# Uses Streamlit's uploader widget to allow the user to upload a csv
uploaded_file = st.file_uploader("Upload a Beauhurst export file (CSV)",type='csv')

# If there is a csv, Streamlit shows it in an expandable dataframe
if uploaded_file is not None:
		file_container = st.expander("Check your uploaded CSV")
		shows = pd.read_csv(uploaded_file)
		uploaded_file.seek(0)
		file_container.write(shows)

		# Creates a dataframe from the uploaded file and creates a list of column names
		df = pd.read_csv(uploaded_file)
		original_names = list(df.columns.values)

		# Renames the column names so there are no spaces and puts the sequential number in the export at the end
		def column_rename(original_names):
			new_names = original_names.copy()
			for i in range(len(new_names)):
				new_names[i] = new_names[i].replace(" (2007) ", "_")
				new_names[i] = new_names[i].replace("Head Office Address - Postcode (if UK)", "Head Office Address - Postcode (if UK)1")
				if bool(re.search(r'\d', new_names[i])) == True:
					digit_position = re.search(r"\d", new_names[i])
					digit_str = new_names[i][digit_position.span()[0]:digit_position.span()[0]+1].strip()
					new_names[i] = new_names[i].replace(digit_str, "")
					new_names[i] = new_names[i]+str(digit_str)
					new_names[i] = new_names[i].replace(" - ", "_")
					new_names[i] = new_names[i].replace(" ", "_")
					new_names[i] = new_names[i].replace("__", "_")
				else:
					new_names[i] = new_names[i].replace(" - ", "_")
					new_names[i] = new_names[i].replace(" ", "_")
			return new_names

		# Creates versions of the columns names that would be suitable as stubs for the Pandas wide to long
		def variable_rename(new_names):
			var_names = new_names.copy()
			for i in range(len(var_names)):
				var_names[i] = re.sub(r'[0-9]+', '', var_names[i])
			return set(var_names)

		# Creating a list of column names for the user to choose from
		static_options = column_rename(original_names)
		
		# Creating lists of column names using Streamlit's multiselect input widget, remove id columns once selected
		static_column_names = st.multiselect("Please select the ID column names. Likely choices are Beauhurst URL, Company name, and Companies House ID.",static_options)
		variable_options = variable_rename([x for x in static_options if x not in static_column_names])
		variable_column_names = st.multiselect("Please select the variable you want to convert from wide to long format. Likely choices are Turnover, Headcount, SIC code, and Postcode.",variable_options)

		# Renaming the dataframe columns with the altered names so that it works in the wide_to_long
		column_dictionary = dict(zip(original_names, static_options))
		df = df.rename(columns=column_dictionary)

		# When the user clicks the button, attempt the wide_to_long using the user inputs
		if st.button('Make the data long'):
			try:
				df_new = pd.wide_to_long(df, stubnames=variable_column_names, i=static_column_names, j="Number")
				@st.cache
				def convert_df(df):
				# IMPORTANT: Cache the conversion to prevent computation on every rerun
					return df.to_csv().encode('utf-8')

				df =df.dropna()
				csv = convert_df(df_new)

				st.download_button(
					label="Download data as CSV",
					data=csv,
					file_name='new_df.csv',
					mime='text/csv',
				)
			except ValueError:
				st.write("Variable column names can't be identical to a column name. Check all column names exist and are correct.")
		else:
			st.write('')

else:
	st.info(
		f"""
			👆 Just add a CSV, no need to alter the column names.
			"""
		)

	st.stop()
