from apscheduler.schedulers.blocking import BlockingScheduler
import os

scheduler = BlockingScheduler()

@scheduler.scheduled_job('interval', hours=4)
def pull_chart_data():
	print('pull_chart_data')
	os.system('python -m scripts.pull_chart_data')

@scheduler.scheduled_job('interval', minutes=10)
def pull_histogram_data():
	print('pull_histogram_data')
	os.system('python -m scripts.pull_histogram_data')

if __name__ == '__main__':
	scheduler.start()