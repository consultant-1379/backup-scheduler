#!/bin/bash
/sbin/sshd

echo '############ Step 1. Run unit tests ##############'
if ! python setup.py test; then
    echo "############ Unit test execution has failed. Exiting the step ##############";
    exit 1
fi

echo '############ Step 2. Run tox ##############'
tox -e build

echo '############ Step 3. Prepare package ##############'
cd dist
pip download enmaas_bur-0.9.2-py2.py3-none-any.whl -d packages/

echo '############ Step 4. Archive package ##############'
tar -czvf bur-packaged.tar.gz packages/

echo '############ All steps were passed successfully ##############'