
cd lambda
zip -X -r ../skill-code.zip .
cd ..
aws lambda update-function-code --function-name HockeyBotEV3 --zip-file fileb://skill-code.zip
rm -rf skill-code.zip