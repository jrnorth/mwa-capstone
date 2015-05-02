In this section, we'll document the basics of how to use the EoRLive version 3 website.

### Navigation
Navigation between pages on the site is done via a header bar at the top of the page. The EoRLive text on the left end of the header bar will take you to the site's home page. On the right side of the bar, when you are logged in, the options `home`, `profile`, `users`, and `log out` will be present. `home` will take you to the home page, `profile` will take you to your page where you can view your data sets and data sources (both of which will be covered in more detail later), and `users` will take you a user directory page where you can view all the site's users and their data sets.

### The Home Page
This page is main page of the site. Here you can look at graphs, create data sets by flagging data, read and write comments, and browse for data sets that are interesting to you.

This page has two date selectors at the top. You can specify a date range you would like to view by selecting a value for each. The main focus of this page is the graph area in the center. You'll notice that there is a series of tabs above the graph: this is where your active data sources will go (which we'll explain later). When you click `Get observations` for the date range you've selected, the graph in the center will reload with the data for that range. Note that the graph's range might not match the range you selected exactly: the start of the graph may be ahead of the start date you specified or the end of the graph may be behind the end date you specified. This is because there may not be data available for the entire range you specified, and the graph is just scaling itself to the range of available data.

The default data source named `Obs_Err` that we have provided will show you a histogram of the observations and telescope errors that occurred in the specified date range; in other words, it will just show you counts of observations and errors. There is special behavior to note in this graph: you can click on any of the error bars and see a table describing the errors that happened in that bar's time range.

#### Creating Data Sets
One of the primary features of the site is creating data sets. A data set is comprised of:
* Start and end dates that serve as bounds
* Any number of flagged ranges of observations between those bounds
* A name
* `high` observations, `low` observations, or both
* `EOR0` observations, `EOR1` observations, or both
* A creator (the user who created it)

Primarily, you will be using graphs in the tabs on the main page to create data sets interactively. As described above, you can select a date range to serve as your set's bounds by specifying start and end dates and clicking `Get observations`. Then, you can select any tab you have on your home page to view that data in the date range you specified.

On any of these graphs, you can click on each series in the legend to show or hide that series on the graph. There is a series of buttons at the top-left of the graph next to the `Zoom` label that allow you to quickly access different zoom levels on the graph. Furthermore, you can click-and-drag horizontally on the graph to manually zoom in to a selected region. Alternatively, you can adjust the blue range selector just below the graph to pan across the data or select a zoom region.

If you are viewing a date range (not a set, as we will explain later), you will see two dropdown menus in the bottom-right corner of the graph next to the `Data set:` label: `High/Low` and `EOR0/EOR1`. These dropdown menus allow you to select different subsets of observations in the range you have selected. `High` corresponds to observations with names that start with 'high', `Low` to observations with names that start with 'low', `EOR0` to observations with an `ra_phase_center` of 0, and `EOR1` to observations with an `ra_phase_center` of 60. You can select any combination of these to change the set of observations shown on the graph.

You can click the checkbox labeled `Enable set construction mode`, which will reveal a panel with some extra controls below. Specifically, you will be shown the start and end dates of the set, and a dropdown labeled `Click + drag:` with the options `Zooms` and `Flags`. The option you choose determines the clicking-and-flagging behavior on the graph. `Zooms` does what you would expect, but `Flags` allows you to manually flag regions of data on the graph by clicking and dragging over the region you want to flag. When you flag a region, a yellow band with a number at the top will show up on the graph over the region you flagged. In the `Flagged sub-ranges` table, you will see a row with a corresponding number. This row will show you the start and end times of the flagged region as well as the number of observations in the region. Finally, there is a button named `Unflag range`. You can click this button to unflag the range, which will remove the yellow band from the graph and the row from the table.

When you are flagging ranges, feel free to overlap them as necessary. For example, if you flag a range but later decide that you need to extend it in either direction, you can just flag a range that overlaps with the existing one and goes in the direction you want. The site will handle merging overlapping ranges for you.

At any time, you can click the `Hide flagged data` checkbox, which will remove all the data you have flagged from the graph. This is useful for getting a better perspective on data in certain graphs: for example, if you're viewing a line graph with a large spike, you won't be able to see the variations in the 'flat' portions of the graph because the scale is so big. You can flag the data and remove it, and the graph will be redrawn with a new scale that allows you to see the 'flat' parts in more detail. As long as the checkbox is checked, any new ranges you flag will remove their associated data from the graph. Unflagging a range will reinsert the data into the graph. To add all the data back to the graph, just uncheck the checkbox.

Once you're done flagging data, you can give your set a name and click `Save set`. If the set was saved successfully, your browser will display an alert that says so.

#### Browsing Data Sets
You can now view your set in the set browser on the right-hand side of the page. There are multiple filtering and sorting options available that allow you to find sets quickly. You can filter by the user who created the set, `EOR0/EOR1`, and `High/Low`. The results can be sorted by the number of data hours in the set in descending order (when your set is saved, the total number of data hours and the number of data hours you flagged in the set is calculated) or by the set creation time in descending order.

The table shows the most important information about each set: the name, creator, number of data hours, whether the set contains `High` observations, `Low` observations, or both, and whether the set contains `EOR0` observations, `EOR1` observations, or both. The set names are hyperlinked, so you can click them to see the corresponding set in detail. Clicking a set hyperlink will reload the page with that set loaded, so you can see all the data that was flagged in the set. You can view the set through any of the data sources you have on your main page.

**Note**: if any of the ranges you flagged didn't contain any observations, they won't show up in your saved set. If there aren't any observations in the range, there is nothing to flag.

Furthermore, you can extend others' sets by making your own modifications and saving them as your own. So, if you're viewing a set, you can click the `Enable set construction mode` checkbox and the table in the revealed panel will be prepopulated with the ranges that are flagged in the set. You can interact with the graph as usual to create your own set, except you're building off the work of others, so you can remove ranges they've flagged or add your own. However, note that the `High/Low` and `EOR0/EOR1` dropdown menus will **not** be available. This is because the set you are viewing already has values for `High/Low` and `EOR0/EOR1` associated with it and you are building off it. When you're done modifying the set, you give it a name and save it as your own.

Below the graph area, you can see the set's details. Next to these are two buttons: `Download set` and `NGAS observations`. `Download set` allows you to download the set as a text file that simply contains a list of all the observations IDs in the set that have not been flagged, one per line. `NGAS observations` will take you to the `Observations` page of the `MWA Administration` site, and the page will already be set to the date range specified by the set. This page allows you to see many more details about the observations in the set.

Note the URL in your browser when you're viewing a set. We designed these URLs to be easy to remember and share. You can access any set by appending `/set/set name` to the end of the site's base URL.

If you're viewing a set, then there will be a message next to the `Get observations` button at the top of the page that says `You are viewing a set (name of the set)`. Even if you're viewing a set, you can select a new date range and click `Get observations`. Note that although the URL doesn't change, the graph will reload but **you will no longer be viewing a set**. The message next to the `Get observations` button will read `You are viewing a date range`. So, if you're ever unsure about whether you're viewing a set or a date range, you can just check the message next to the button.

Above the data set browser is a table that displays some summary statistics for the date range you selected (or the date range corresponding to the set you selected). It shows the hours of data and observation counts for each of the `High/Low` and `EOR0/EOR1` subsets, as well as the total number of telescope errors that occurred in the date range.

#### Comments
Below the graph area, we've provided a basic comment section that is meant to serve as a place for discussions about data sets. You can link to sets in comments (not in thread titles) using a special syntax: @set(name of the set). Type the set's name as-is.

### The Profile Page
Your profile page is a place for you to upload sets via text files, create and manage your data sources, and view your sets.

#### Uploading Sets
You can upload a set to the site using a text file. Your text file should contain only observation IDs, and only one per line (can there be empty lines?). The text file is interpreted as follows: all the observation IDs in the file are assumed to be "good" and will not be flagged, and any observation IDs in the gaps between the observation IDs provided in the file will be flagged.

Note that you need to specify whether the data set you're uploading contains `High` observations, `Low` observations, or both (`Any`), and also whether it contains `EOR0` observations, `EOR1` observations, or both (`Any`) via two dropdown menus. If you upload a set that contains observation IDs that aren't found in the set of observations that corresponds to the options you selected, you will receive an error. So, if the set you're uploading contains data from both `Low` and `High` or `EOR0` and `EOR1` (or if you're not sure), you can just put `Any` for either or both of the dropdowns.

#### Your Sets
On the profile page, you can view a list of all the sets you've created and delete them if they're no longer necessary. Deleting a set will **not** affect any sets created by other users that were modifications of the deleted set.

#### Creating Data Sources
A data source is basically a subset of numeric columns in a single table in a database paired with a graph type. Essentially, each column you choose will be its own data series in the graph. We've provided basic column and line graphs, but you can [create your own graph types](https://github.com/dhganey/mwa-capstone/wiki/Adding-Custom-Graph-Types). Data sources are extremely useful in that you can use them to view specific data for any date range or set on the site!

To start, choose a database by entering the host URL and the database name. Click `View tables` to attempt to connect to the database. If you connected successfully, you will see a dropdown menu that lists all the tables in the database. Select a table and you will be presented with a list of all the numeric columns in that table. Check the boxes next to the columns you want as data series in your graph. Then, because we will fetch the data based on the assumption that the table is indexed by observation IDs in some way, you need to type in the name of the column that contains the observation IDs. **Important**: do **not** check the name of the column you type here in the above list! Finally, you must give your data source a unique name.

Click `Create data source`. If your data source was created successfully, it will appear under `Your Data Sources`.

#### Active Data Sources
As explained [above](https://github.com/dhganey/mwa-capstone/wiki/Website-Usage#the-home-page), your active data sources will appear as tabs on your home page. To update your active data sources, just check the data sources you want to appear on your home page and click `Update active`. If you no longer want a data source, just click `Remove from yours` and it will return to the `Available Data Sources`.

#### Available Data Sources
Any data sources created on the site will be available for all users to see and use. You can browse available data sources in the `Available Data Sources` list. If you want to use one, just click `Add to yours` and it will appear under `Your Data Sources`. From there, you can choose to add it to your active data sources as explained above.