# Summary

The KBase Assembly Service REST interface returns JSON messages.

# Job

## Get one job

/user/{user.id}/job/{?report}

## Status of a job

/user/{user.id}/job/{job.id}/status

## File info for all results of a job

/user/{user.id}/job/{job.id}/results{?type,tags}

# User

## user's data info

/user/{user.id}/data
/user/{user.id}/data/{data.id}

# Apps

## Modules available for pipeline

/module/all
/module/avail

example: http://140.221.84.124:8000/module/avail

## Recipes available for pipeline
/recipe/avail
/recipe/all

### Recipe Info

#### All Info

/recipe/velvet

#### Raw Lisp Expression

/recipe/velvet/raw

#### Description

/recipe/velvet/description

# Blob storage

## Get Shock host URL

/shock

example: http://140.221.84.124:8000/shock

## More on shock

- Assembly service uses Shock as its blob storage appliance
- see https://github.com/MG-RAST/Shock
- see https://github.com/MG-RAST/Shock/wiki/API

example: http://140.221.84.205:8000/node/7373a98f-9135-4b91-85f9-2bb840444436?download
