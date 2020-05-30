```
cd ~/projects/kodi/script.module.clouddrive.common

docker run -it --rm --name=kodi \
  -v $(pwd)/:/home/kodi/.kodi/addons/script.module.clouddrive.common/ `# mount the addon; needs to be enabled in kodi config`\
  lasery/codebench:kodi \
  bash

cd ~/.kodi/addons/script.module.clouddrive.common/
python fork/tests.py
cat /home/kodi/.kodi/temp/kodi.log
```

