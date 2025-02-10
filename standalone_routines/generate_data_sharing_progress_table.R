library(httr2)
library(knitr)
library(tidyverse)

# insert start date (YYMMDD)
date_start <- '240101'
# insert end date (YYMMDD)
date_end <- '250101'

# define columns to group by and report in output table
cols_group_by <- c('clusters','provider')
cols_reporting <- c('num_discoverable','num_public','num_published','num_unknown')

# pull datasets from public discovery endpoint: https://github.com/cznethub/dsp-reports
dsp_datasets_df <- request(
  'https://dsp-reports-jbzfw6l52q-uc.a.run.app/csv') %>%
  # the request can take a minute or two, retries set arbitrarily 
  req_retry(max_tries = 5) %>%
  req_timeout(seconds = 120) %>%
  # perform request and interpret response as text 
  req_perform() %>%
  resp_body_string() %>%
  # read in csv, skip first column (index)
  read_csv(col_types = 
             cols(...1 = col_skip())) %>%
  # convert date columns
  mutate(datePublished=as.Date(datePublished),
         dateCreated=as.Date(dateCreated)) %>%
  # filter datasets after project start (after Jan 1 2020; before this is from CZO project)
  filter(dateCreated>=as.Date('2020-01-01')) %>%
  # explicitly remove CZO or Hub affilated datasets
  filter(!str_detect(clusters, 'CZO|CZNet Hub')) %>%
  # remove json string elements
  mutate(across(everything(), ~gsub("\\[|'|\\]", "", .))) %>%
  # replace empty strings with na
  mutate(across(everything(), ~na_if(., ""))) %>%
  # remove datasets with no cluster information (~8%)
  drop_na(clusters) %>%
  # change NA access status to unknown (this is the case for Zenodo datasets)
  mutate(access = replace_na(access, "UNKNOWN"))

dsp_datasets_df

dsp_datasets_progress_df <- dsp_datasets_df %>%
  # create a new date column to correspond to initial share date OR publish date
  mutate(Date=ifelse(access=='PUBLISHED',datePublished,dateCreated)) %>%
  # filter between time range of interest
  filter(Date>=as.Date(date_start,format='%y%m%d') & Date <=as.Date(date_end,format='%y%m%d')) %>%
  # add numeric columns for access level for each dataset (1=True, 0=False)
  mutate(
    num_discoverable = ifelse(grepl('DISCOVERABLE', access), 1, 0),
    num_public = ifelse(grepl('PUBLIC', access), 1, 0), 
    num_published = ifelse(grepl('PUBLISHED', access), 1, 0),
    num_unknown = ifelse(grepl('UNKNOWN', access), 1, 0)
  ) %>%
  # select columns of interest
  select(cols_group_by,cols_reporting) %>%
  # sum all the number of datasets by provider and access level 
  group_by(across(all_of(cols_group_by))) %>%
    summarise(
      num_discoverable = sum(num_discoverable, na.rm = TRUE),
      num_public = sum(num_public, na.rm = TRUE),
      num_published = sum(num_published, na.rm = TRUE),
      num_unknown = sum(num_unknown, na.rm = TRUE),
      .groups = "drop"
    ) %>%
  # arrange by cluster then provider for readability
  arrange(across(all_of(cols_group_by))) %>%
  # create total row across clusters and providers
  bind_rows(
    summarise(
      .,
      clusters = "All",
      provider = "All",
      num_discoverable = sum(num_discoverable, na.rm = TRUE),
      num_public = sum(num_public, na.rm = TRUE),
      num_published = sum(num_published, na.rm = TRUE),
      num_unknown = sum(num_unknown, na.rm = TRUE),
      .groups = "drop"
    )
  ) 

# generate human readable table in markdown for reporting
kable(dsp_datasets_progress_df,format='markdown')

# report clusters without data shared in this time period
clusters <- unique(dsp_datasets_df$clusters)
clusters_with_datasets <- unique(dsp_datasets_progress_df$clusters)
clusters_without_datasets <- clusters[!clusters %in% clusters_with_datasets]
sprintf('Clusters without datasets shared in time range: %s', 
        paste0(clusters_without_datasets, collapse = ', '))