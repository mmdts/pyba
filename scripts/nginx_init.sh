echo "This script is meant to run on a Linux operating system. Your hosts file and nginx config in windows"
echo "have different locations to the ones listed in this script. Please modify it accordingly then run."
echo ""
echo "If not running this script as sudo, please do."
echo "Please install nginx before running this script."
echo ""
echo "If everything goes successfully, you can access the game by running:"
echo "python3 main.py --mode=play"
echo "then visiting http://barbarianassault.local on a browser."
cat hosts >> /etc/hosts
cp pyba.nginx /etc/nginx/sites-enabled/
