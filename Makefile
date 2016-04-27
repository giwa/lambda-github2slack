all: clean build main

build:
	pip install PyGithub -t .

main:
	zip -r review_reminder.zip .

clean:
	rm -rf github PyGithub-*
	rm -rf review_reminder.zip
