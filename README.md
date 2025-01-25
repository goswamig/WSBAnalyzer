## Configuration
1. Copy `.env.example` to `.env`
2. Fill in your credentials in `.env`
3. Never commit `.env` file

## Required Credentials
- Reddit API credentials (create at https://www.reddit.com/prefs/apps)
- OpenAI API key
- Gmail account with App-specific password


## For Docker
1. To Run the service: `docker-compose up -d`
2. To Stop the service: `docker-compose down`
3. To check logs: `docker-compose logs -f`

## IF you just want to build a Docker image 
1. `docker build -t wsb -f docker/Dockerfile .`

## you can pull image
`docker pull wsbsummary/v0.1:latest`
