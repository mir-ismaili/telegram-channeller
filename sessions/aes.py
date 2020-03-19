import base64
import os
from os import listdir
from os.path import isfile, join

import aiofiles
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


def cbc_encrypt(data, key):
    cipher = AES.new(key, AES.MODE_CBC)
    encrypted = cipher.encrypt(pad(data, AES.block_size))
    return encrypted, cipher.iv


def cbc_decrypt(encrypted, key, iv):
    return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(encrypted), AES.block_size)


def urlsafe_b64encode_with_no_padding(name_as_bytes):
    return base64.urlsafe_b64encode(name_as_bytes).rstrip(b'=').decode('ascii')


def urlsafe_b64decode_with_no_padding(encoded):
    return base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))


AES_KEY = bytes.fromhex(os.environ.get('AES_KEY'))
path = './sessions'
SUF1 = '.session'
SUF2 = '.encrypted'


async def encrypt_sessions():
    file_names = [f for f in listdir('.') if isfile(join('.', f)) and f.endswith(SUF1)]

    for file_name in file_names:
        async with aiofiles.open(file_name, 'rb') as in_file:
            data = await in_file.read()

        encrypted, iv = cbc_encrypt(data, AES_KEY)

        encrypted_name, name_iv = cbc_encrypt(file_name[:-len(SUF1)].encode(), AES_KEY)

        encrypted_file_name = urlsafe_b64encode_with_no_padding(encrypted_name) + SUF1 + SUF2

        async with aiofiles.open(join(path, encrypted_file_name), 'wb') as out_file:
            [await out_file.write(x) for x in (name_iv, iv, encrypted)]

        # test:
        decrypted = cbc_decrypt(encrypted, AES_KEY, iv)
        print('%s "%s" "%s"' % (data == decrypted, file_name, encrypted_file_name))


async def decrypt_sessions():
    file_names = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith(SUF1 + SUF2)]

    for encrypted_file_name in file_names:
        async with aiofiles.open(join(path, encrypted_file_name), 'rb') as in_file:
            name_iv, iv, encrypted = [await in_file.read(x) for x in (AES.block_size, AES.block_size, -1)]

        data = cbc_decrypt(encrypted, AES_KEY, iv)

        b64_part = encrypted_file_name[:-len(SUF1) - len(SUF2)]
        file_name = cbc_decrypt(urlsafe_b64decode_with_no_padding(b64_part), AES_KEY, name_iv).decode() + SUF1

        if os.path.exists(file_name):
            async with aiofiles.open(file_name, 'rb') as in_file:
                print('%s "%s" "%s"' % (await in_file.read() == data, encrypted_file_name, file_name))
        else:
            async with aiofiles.open(file_name, 'wb') as out_file:
                await out_file.write(data)

# # test:
# import asyncio
#
# loop = asyncio.get_event_loop()
# # Run the first function on local machine (to encrypt). Then run the second here for test:
# # loop.run_until_complete(encrypt_sessions())
# loop.run_until_complete(decrypt_sessions())
