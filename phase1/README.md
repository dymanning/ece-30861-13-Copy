## Workflow 
This guide explains how we will use GitHub Issues, Branches, Pull Requests, and the Project Board to manage our work.

### Project Board
The GitHub Project board has 4 columns
* **To Do** - tasks we haven't started yet.
* **In Progress** - tasks someone is currently working on
* **In Review** - tasks with an open pull requests
* **Done** - merged and finished tasks

Each issue is linked to a card on this board

### Workflow for Each Task
#### 1. Open an Issue
If you want to take on an issue on the ToDo list, assign yourself and go to step 2.

If you want to creat a new issue, use the following guidelines
* From the repo home page click issues to open the page of all of the issues.
* Click New Issue.
* Write a short title leading with feat: bug: or fix: depending on the type of issue.
* Write a short description with relevant details for the issue.
* On the right hand side make sure to link to the project board and assign someone if you want to.
* Click create issue and the issue should be linked to the project board.

#### 2. Create a Branch
Each time you write code to work on an issue. You should create a branch to write code in.

```
git checkout -b issue-<number>-short-description
```
For example
```
git checkout -b issue-23-license-metric
```

#### 3. Do the Work
* Commit the changes regularly with meaningful commit messages
```
git commit -m "commit message"
```
* Push you branch to github to save your work in the cloud
```
git push -u origin issue-<number>-short-description
```

#### 4. Open a Pull Request (PR)
* In the PR description, include "Fixes #<issue number>" so the issue closes automatically after merge.

Example PR title
```
Fixes #23: Implement LicenseMetric
```

* Move the task card to In Review

#### 5. Merge and Close
* Once the Pull Request is reviewed merge the PR into main.
* The linked issue will close automatically.
* The card will move to done on the project board.