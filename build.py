# -*- coding: utf-8 -*-

import os
import re
import shutil
import subprocess
import sys

import pinyin

gl_default_timeout = 180
gl_clean_before_build = False
gl_output_dir = '/home/youxue/opt/workspace/apks/ue6'
gl_apps_exclude = ()

gl_priority_dir = ['PublicModule']
gl_platform_app = ['com.youshiyouxue.noahappstore', 'com.noahedu.pmc', 'com.youshiyouxue.basisservice']


# gl_apps_exclude = ('PublicModule')

def to_pinyin(var_str):
    if isinstance(var_str, str):
        if var_str == 'None':
            return ""
        else:
            return pinyin.get(var_str, format='strip', delimiter="")
    else:
        return '类型不对'


def convert_pinyin(dir_name):
    for dir_path, dir_names, file_names in os.walk(dir_name):
        for filename in file_names:
            dst_name = to_pinyin(filename)
            print('dst_name=%s' % dst_name)
            src_path = os.path.join(dir_path, filename)
            dst_path = os.path.join(dir_path, dst_name)
            # print(src_path + '->' + dst_name)
            os.rename(src_path, dst_path)


def run_cmd(cmd, log_path, log_cmd=True, print_output=False):
    if log_cmd:
        print("[run_cmd]=%s" % cmd)
    run_cmd_result = False
    tmp_file = open(log_path, 'a+')
    if log_cmd:
        tmp_file.write(cmd)
        tmp_file.write('\n')

    res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        value = res.poll()
        if value is None:
            sys.stdout.flush()
            out_line = res.stdout.readline()
            out_line = out_line.strip()
            if out_line:
                tmp_file.write(out_line)
                tmp_file.write('\n')
                if print_output:
                    print out_line
        else:
            tmp_file.close()
            if value == 0:
                run_cmd_result = True
                print('[run_cmd] success!')
            else:
                print('WARNING: Exec cmd failed! See log for more details:%s' % log_path)

            break

    return run_cmd_result


def run_common_cmd(cmd, work_dir=None):
    print('[run_common_cmd]:%s work dir is %s' % (cmd, work_dir))
    run_common_cmd_result = False
    if work_dir is None:
        res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               executable="/bin/bash")
    else:
        res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=work_dir,
                               executable="/bin/bash")

    while True:
        value = res.poll()
        if value is None:
            sys.stdout.flush()
            out_line = res.stdout.readline()
            out_line = out_line.strip()
            if out_line:
                print out_line
        else:
            if value == 0:
                run_common_cmd_result = True
                print('[run_common_cmd] Success!')
            else:
                print('[run_common_cmd] Failed!')

            break

    return run_common_cmd_result


def exec_command(command):
    # print('[exec_command]:%s' % command)
    output = ''
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError, exc:
        print(exc.cmd)
        print(exc.returncode)
        print(exc.output)

    return output


def copy_apks(src_dir, dst_dir):
    list = os.listdir(src_dir)  # 列出文件夹下所有的目录与文件
    for i in range(0, len(list)):
        path = os.path.join(src_dir, list[i])
        if os.path.isfile(path):
            # print '==>', path
            if path.endswith('.apk'):
                # print '==>', path
                tmp_dir, tmp_name = os.path.split(path)
                # print tmp_dir
                # print tmp_name
                shutil.copyfile(path, dst_dir + tmp_name)


def copy_file(src_file, dst_file):
    # print '[copy_file] from ', src_file
    # print '[copy_file] to ', dst_file
    shutil.copyfile(src_file, dst_file)


def get_apk_info(apk_file):
    output = exec_command('aapt dump badging ' + apk_file)
    # print output
    tmp_packages = re.findall(r'package: name=\'(.+?)\'', output)
    tmp_versions = re.findall(r'versionCode=\'(.+?)\'', output)
    # print 'tmp_packages = ', tmp_packages
    package_name = tmp_packages[0]
    version = int(tmp_versions[0])
    # print 'package_name = ', package_name
    # print 'version = ', version
    create_time = os.path.getctime(apk_file)
    return package_name, version, create_time


def copy_so(arch, src_file, to_dir):
    if arch in src_file:
        tmp_dir = os.path.join(to_dir, arch)
        create_dir(tmp_dir)
        c = 'cp ' + src_file + " " + tmp_dir
        exec_command(c)


def safe_copy_so(src_file, to_dir):
    copy_so('arm64-v8a', src_file, to_dir)
    copy_so('armeabi', src_file, to_dir)
    copy_so('armeabi-v7a', src_file, to_dir)


def safe_copy_apk(src_file, to_dir, log_path):
    # print '[safe_copy_apk] %s to %s' % (src_file, to_dir)

    src_package_name, src_version, create_time = get_apk_info(src_file)
    # print 'package_name = %s, version = %s' % (src_package_name, src_version)

    lower_version_apk_list = []
    files = os.listdir(to_dir)
    for tmp_file in files:
        path = os.path.join(to_dir, tmp_file)
        if os.path.isfile(path):
            if tmp_file.endswith('.apk'):
                tmp_package_name, tmp_version, create_time = get_apk_info(path)
                if src_package_name == tmp_package_name:
                    # print 'path = %s, package_name = %s, version = %s' % (path, tmp_package_name, tmp_version)
                    if src_version >= tmp_version:
                        lower_version_apk_list.append(path)

    # 删除低版本的apk
    for apk_path in lower_version_apk_list:
        os.remove(apk_path)
    name = os.path.basename(src_file)
    # 把新的apk拷贝到目标文件夹下
    dst_file = os.path.join(to_dir, name)
    copy_file(src_file, dst_file)

    # 对新apk签名生成新的签名过的apk
    # 删除新的apk
    # 修改新生成的签名过的apk的权限
    is_platform_app = False
    for tmp in gl_platform_app:
        if tmp == src_package_name:
            is_platform_app = True
            break

    if is_platform_app:
        apk_file_signed = sign_system_apk(dst_file, log_path)
    else:
        apk_file_signed = sign_apk(dst_file, log_path)
    if os.path.exists(dst_file):
        os.remove(dst_file)
    run_cmd('chmod 777 ' + apk_file_signed, log_path)


def sign_apk(src_file, log_path):
    dst_dir = os.path.dirname(src_file)
    base_name = os.path.basename(src_file);
    dst_name = base_name.replace('.apk', '-signed.apk')
    print 'dst_name = ', dst_name
    p12_file = '/home/youxue/opt/workspace/update/keystore/release/release.p12'
    cmd = 'jarsigner -verbose -keystore ' + p12_file
    dst_path = os.path.join(dst_dir, dst_name);
    if os.path.exists(dst_path):
        os.remove(dst_path)
    cmd = cmd + ' -storepass YOUSHI#youxue@';
    cmd = cmd + ' -signedjar ' + dst_path
    cmd = cmd + ' ' + src_file
    cmd = cmd + ' youshiyouxue'
    run_cmd(cmd, log_path, False)
    return dst_path


def sign_system_apk(src_file, log_path):
    dst_dir = os.path.dirname(src_file)
    base_name = os.path.basename(src_file);
    dst_name = base_name.replace('.apk', '-signed.apk')
    print '==>dst_name = ', dst_name

    key_dir = '/home/youxue/opt/workspace/update/keystore/release/platform/'
    x509_file = key_dir + 'platform.x509.pem'
    pk8_file = key_dir + 'platform.pk8'
    sign_file = key_dir + 'signapk.jar'
    cmd = 'java -Djava.library.path='
    cmd += key_dir
    cmd += '  -jar  ' + sign_file
    dst_path = os.path.join(dst_dir, dst_name);
    if os.path.exists(dst_path):
        os.remove(dst_path)
    cmd = cmd + ' ' + x509_file
    cmd = cmd + ' ' + pk8_file
    cmd = cmd + ' ' + src_file
    cmd = cmd + ' ' + dst_path
    run_cmd(cmd, log_path, True)
    # print('dst_path=%s' % dst_path)
    return dst_path


# 先比较版本号，再比较创建时间
def apk_compare(apk_info1, apk_info2):
    if apk_info1[0] > apk_info2[0]:
        return -1
    elif apk_info1[0] < apk_info2[0]:
        return 1
    else:
        if apk_info1[1] > apk_info2[1]:
            return -1
        elif apk_info1[1] < apk_info2[1]:
            return 1
    return 0


# 从apk列表中查找版本号最高或者修改时间最新的apk
def find_latest_apk(all_apk_paths):
    if len(all_apk_paths) <= 0:
        return None
    elif len(all_apk_paths) <= 1:
        return all_apk_paths

    apk_dict = {}
    for apk_path in all_apk_paths:
        package_name, version, create_time = get_apk_info(apk_path)
        tmp_value = [version, create_time, apk_path]
        if not apk_dict.has_key(package_name):
            apk_dict[package_name] = []
        apk_dict[package_name].append(tmp_value)

    for key in apk_dict:
        apk_dict[key].sort(apk_compare)

    print(apk_dict)

    result = []
    for key in apk_dict:
        result.append(apk_dict[key][0][2])

    # print(result)
    return result


def search_and_copy_apk(from_dir, to_dir, log_path):
    # 搜索from_dir所有的apk(debug或者release模式)
    all_apk_paths = []
    all_so_paths = []
    for root, dirs, files in os.walk(from_dir):
        for name in files:
            if str(name).endswith(".apk"):
                src_file = os.path.join(root, name)
                dir_name = os.path.dirname(src_file)
                if dir_name.endswith('debug') or dir_name.endswith('release'):
                    all_apk_paths.append(src_file)
            elif str(name).endswith(".so"):
                src_file = os.path.join(root, name)
                if 'mergeJniLibs/release' in src_file:
                    all_so_paths.append(src_file)

    latest_apk = find_latest_apk(all_apk_paths)
    if latest_apk is not None:
        for tmp in latest_apk:
            print("latest_apk = %s" % tmp)
            safe_copy_apk(tmp, to_dir, log_path)

    if all_so_paths is not None:
        for tmp in all_so_paths:
            safe_copy_so(tmp, to_dir)


def is_app_need_build(app):
    for tmp in gl_apps_exclude:
        if app == tmp:
            return False;
    return True


def build_app(path, to_dir, log_dir):
    base_name = os.path.basename(path)
    print('[build_app] start build: ' + base_name)
    build_app_result = True
    log_path = os.path.join(log_dir, base_name + '.log')
    if os.path.isdir(path) and is_app_need_build(base_name):
        gradle_path = os.path.join(path, 'build.gradle')
        if os.path.exists(gradle_path):
            # print gradle_path
            if gl_clean_before_build:
                run_cmd("gradle clean -b " + gradle_path, log_path)
            # run_cmd('svn update ' + path + ' --username lining --password lining', log_path, False)
            update_app_and_save_log(path)
            build_app_result = run_cmd("gradle assembleRelease -b " + gradle_path, log_path)
            # print output
            if build_app_result:
                search_and_copy_apk(path, to_dir, log_path)
            else:
                build_app_result = False
        else:
            print('WARNING: ' + gradle_path + ' not exists!')

    print('[build_app] end build: ' + base_name + ' ' + str(build_app_result))
    return build_app_result


def remove_control_chars(s):
    control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
    control_char_re = re.compile('[%s]' % re.escape(control_chars))
    return control_char_re.sub('', s)


def update_app_and_save_log(path):
    base_name = os.path.basename(path)
    # print('base_name = %s' % base_name)
    user_info = ' --username lining --password lining'
    cmd_svn_info = 'svn info ' + path + user_info + ' | grep \'Last Changed Rev\' | sed \'s/Last Changed Rev: //\''
    str_rev1 = exec_command(cmd_svn_info)
    str_rev1 = remove_control_chars(str_rev1)

    # print('str_rev1 = %s' % str_rev1)

    cmd_update = 'svn update ' + path + user_info
    exec_command(cmd_update)

    str_rev2 = exec_command(cmd_svn_info)
    # print('str_rev2 = %s' % str_rev2)
    str_rev2 = remove_control_chars(str_rev2)

    if str_rev1.strip() == '' or str_rev2.strip() == '':
        return

    if str_rev2 == str_rev1:
        return

    submit_dir = get_submit_dir()
    # print('submit_dir = %s' % submit_dir)
    submit_path = os.path.join(submit_dir, base_name + "_changelist.txt")
    # print('submit_path = %s' % submit_path)

    cmd_save_log = 'svn log -r ' + str_rev1 + ':' + str_rev2 + ' ' + path + user_info + ' >> "' + submit_path + '"'
    exec_command(cmd_save_log)


def dir_compare(dir1, dir2):
    for tmp in gl_priority_dir:
        if tmp == dir1:
            return -1
    return 0


def build_all_apps(from_dir, to_dir, log_dir):
    build_all_apps_result = True
    file_list = os.listdir(from_dir)
    file_list.sort(dir_compare)

    print('[build_all_apps] prepare......\n')
    for tmp in file_list:
        print('        ' + tmp)

    print('\n')
    print('[build_all_apps] start......\n')

    log_path = os.path.join(get_log_dir(), 'all.log')
    file_log = open(log_path, 'a+')

    for tmp_file in file_list:
        s = build_app(os.path.join(from_dir, tmp_file), to_dir, log_dir)
        file_log.write('build ' + tmp_file + ' ' + str(s))
        file_log.write('\n')
        if not s:
            build_all_apps_result = False
        print('\n')

    file_log.close()
    return build_all_apps_result


def get_lint_dir():
    lint_dir = gl_output_dir + '/lints/'
    create_dir(lint_dir)
    return lint_dir


def get_release_dir():
    release_dir = gl_output_dir + '/release/'
    create_dir(release_dir)
    return release_dir


def get_youshiyouxue_apks_dir():
    tmp_dir = gl_output_dir + '/release/apps/'
    create_dir(tmp_dir)
    return tmp_dir

def get_third_so_dir():
    tmp_dir = '/home/youxue/opt/workspace/jenkins/workspace/test/ue6/third_so'
    create_dir(tmp_dir)
    exec_command('svn update ' + dir + ' --username lining --password lining')
    return tmp_dir


def get_bambu_dir():
    tmp_dir = gl_output_dir + '/bambu/'
    create_dir(tmp_dir)
    return tmp_dir


def get_inner_system_apks_dir():
    tmp_dir = '/home/youxue/opt/workspace/jenkins/workspace/test/ue6/inner'
    create_dir(tmp_dir)
    exec_command('svn update ' + tmp_dir + ' --username lining --password lining')
    return tmp_dir


def get_third_apks_dir():
    tmp_dir = gl_output_dir + '/release/third/'
    create_dir(tmp_dir)
    return tmp_dir


def get_log_dir():
    log_dir = '/home/youxue/opt/workspace/apks/ue6/logs/'
    create_dir(log_dir)
    return log_dir


def get_submit_dir():
    log_dir = '/home/youxue/opt/workspace/apks/ue6/submitlogs/'
    create_dir(log_dir)
    return log_dir


def get_system_release_dir():
    log_dir = '/home/youxue/opt/workspace/ue6/system_release/'
    create_dir(log_dir)
    return log_dir


def create_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def copy_apk_to_system_app(apks_dir):
    system_app_dir = get_system_release_dir() + 'release/target_data/SYSTEM/app'
    file_list = os.listdir(apks_dir)
    for tmp_file in file_list:
        apk_path = os.path.join(apks_dir, tmp_file)
        if apk_path.lower().endswith('.apk'):
            src_package_name, src_version, create_time = get_apk_info(apk_path)
            dst_dir = os.path.join(system_app_dir, src_package_name)
            create_dir(dst_dir)
            copy_file(apk_path, os.path.join(dst_dir, src_package_name + ".apk"))


def del_some_system_app():
    system_app_dir = get_system_release_dir() + 'release/target_data/SYSTEM/app/'
    home_app_dir = system_app_dir + 'Lighthome'
    exec_command('rm -fr ' + home_app_dir)


def main_work(src_dir):
    # 删除日志文件
    del_all_files_in_dir(get_log_dir())
    return build_all_apps(src_dir, get_youshiyouxue_apks_dir(), get_log_dir())


def del_all_files_in_dir(dir):
    if os.path.exists(dir):
        file_list = os.listdir(dir)
        if file_list is not None:
            for tmp_file in file_list:
                path = os.path.join(dir, tmp_file)
                os.remove(path)


# 拷贝第三方apk到目标文件夹下
def copy_third_apks(dst_dir):
    dir = '/home/youxue/opt/workspace/jenkins/workspace/test/ue6/third'
    exec_command('svn update ' + dir + ' --username lining --password lining')
    file_list = os.listdir(dir)
    print(file_list)
    for tmp_file in file_list:
        apk_path = os.path.join(dir, tmp_file)
        if apk_path.lower().endswith('.apk'):
            copy_file(apk_path, os.path.join(dst_dir, tmp_file))


def get_default_project_dir():
    jenkins_home = os.getenv('JENKINS_HOME')
    print 'jenkins_home = ', jenkins_home

    project_dir = jenkins_home + '/workspace/test/ue6/android/'
    print('project_dir = %s' % project_dir)
    return project_dir


def build_default_project():
    main_work(get_default_project_dir())
    copy_third_apks(get_third_apks_dir())


def change_version(path, tmp_version):
    with open(path, 'r') as f1:
        line_list = f1.readlines()
        i = 0
        for tmp in line_list:
            if 'ro.product.version' in tmp:
                line_list[i] = 'ro.product.version=' + tmp_version + '\n'
            i = i + 1

    f = open(path, 'w')
    for tmp in line_list:
        f.write(tmp)
    f.close()


def build_system():
    source_dir = '/home/youxue/opt/workspace/ue6/ue6'
    os.chdir(source_dir)
    run_common_cmd('source /home/youxue/opt/workspace/update/build_system.sh', work_dir=source_dir)

    test = False
    if test:
        run_common_cmd('source /home/s912/othertools/TOOLSENV.sh')
        run_common_cmd('source ./script/build.sh all', work_dir=source_dir)
        # run_common_cmd([".", "./script/build.sh all"])
        run_common_cmd('source ./script/update_release.sh', work_dir=source_dir)

    os.chdir('/home/youxue/opt/workspace/ue6/system_release/release')
    run_common_cmd('rm -fr target_data/')
    run_common_cmd('cp -fr target_files/ target_data/')


def copy_apks_and_so():
    # 拷贝预置应用
    copy_apk_to_system_app(get_youshiyouxue_apks_dir())
    copy_apk_to_system_app(get_inner_system_apks_dir())
    del_some_system_app()

    # 拷贝so
    system_lib64_dir = get_system_release_dir() + 'release/target_data/SYSTEM/lib64'
    command_copy_system_lib64 = 'cp ' + get_youshiyouxue_apks_dir() + 'arm64-v8a/*.so ' + system_lib64_dir
    exec_command(command_copy_system_lib64)

    system_lib_dir = get_system_release_dir() + 'release/target_data/SYSTEM/lib'
    command_copy_system_lib = 'cp ' + get_youshiyouxue_apks_dir() + 'armeabi/*.so ' + system_lib_dir
    exec_command(command_copy_system_lib)
    command_copy_system_lib = 'cp ' + get_youshiyouxue_apks_dir() + 'armeabi-v7a/*.so ' + system_lib_dir
    exec_command(command_copy_system_lib)

    #拷贝第三方so
    # copy_third_so()

    # 拷贝预安装应用
    preinstall_app_dir = get_system_release_dir() + 'release/target_data/SYSTEM/preinstall'
    create_dir(preinstall_app_dir)
    command_copy_preinstall_apps = 'cp -fr ' + get_third_apks_dir() + '*.apk ' + preinstall_app_dir
    exec_command(command_copy_preinstall_apps)
    convert_pinyin(preinstall_app_dir)


def copy_bambu():
    system_dir = get_system_release_dir() + 'release/target_data/SYSTEM/'
    command_copy_bambu = 'cp -fr ' + get_bambu_dir() + '* ' + system_dir
    exec_command(command_copy_bambu)

def copy_third_so():
    system_lib64_dir = get_system_release_dir() + 'release/target_data/SYSTEM/lib64'
    command_copy_system_lib64 = 'cp ' + get_third_so_dir() + 'arm64-v8a/*.so ' + system_lib64_dir
    exec_command(command_copy_system_lib64)

    system_lib_dir = get_system_release_dir() + 'release/target_data/SYSTEM/lib'
    command_copy_system_lib = 'cp ' + get_third_so_dir() + 'armeabi/*.so ' + system_lib_dir
    exec_command(command_copy_system_lib)
    command_copy_system_lib = 'cp ' + get_third_so_dir() + 'armeabi-v7a/*.so ' + system_lib_dir
    exec_command(command_copy_system_lib)


def build_tf_and_ota():
    release_dir = '/home/youxue/opt/workspace/ue6/system_release/release'
    os.chdir(release_dir)
    change_version(get_system_release_dir() + 'release/target_data/SYSTEM/build.prop', version)

    if build_inc_package:
        run_common_cmd('source /home/youxue/opt/workspace/update/build_tf_and_ota_inc.sh', work_dir=release_dir)
    else:
        run_common_cmd('source /home/youxue/opt/workspace/update/build_tf_and_ota.sh', work_dir=release_dir)

    test = False
    if test:
        run_common_cmd('source /home/youxue/opt/workspace/ue6/ue6/build/java_envsetup.sh')
        run_common_cmd('source ./build_ota_pkg.sh', work_dir=release_dir)


# python build.py -c 文件夹
if __name__ == '__main__':
    print(sys.argv)

    size = len(sys.argv)

    remove_submit_logs = False
    build_tf_package = False
    rebuild_tf_package = False
    build_inc_package = False
    test_copy_inner = False
    use_bambu = False

    version = ''
    for param in sys.argv:
        if param.startswith('-'):
            if param == '-c':
                gl_clean_before_build = True
            if param == '-r':
                remove_submit_logs = True
            if param == '--tf':
                build_tf_package = True
            if param == '--repackage':
                rebuild_tf_package = True
            if param == '--ota':
                build_inc_package = True
            if param == '--bambu':
                use_bambu = True
            if param == '--testcopy':
                test_copy_inner = True
            if '--version=' in param:
                version = param[10:]

    if remove_submit_logs:
        submit_dir = get_submit_dir()
        if os.path.exists(submit_dir):
            dirs = os.listdir(submit_dir)
            for tmp_submit_log_file in dirs:
                if os.path.exists(tmp_submit_log_file):
                    os.remove(tmp_submit_log_file)

    project_path = sys.argv[size - 1]
    print('project_path = %s' % project_path)
    print('version = %s' % version)

    if os.path.exists(project_path):
        if os.path.isdir(project_path):
            build_app(project_path, get_youshiyouxue_apks_dir(), get_log_dir())
        else:
            print('%s is a file! Build the default project.' % project_path)
            build_default_project()
    else:
        if build_tf_package:
            print('start build TF and OTA package!')
            main_work_result = main_work(get_default_project_dir())
            if main_work_result:
                print('build all apps success!')
                third_dir = get_third_apks_dir()
                copy_third_apks(third_dir)

                # 开始编译系统
                build_system()

                copy_apks_and_so()
                if use_bambu:
                    copy_bambu()

                # 开始编译TF卡升级包和OTA包
                build_tf_and_ota()
            else:
                print('WARNING: build all apps failed!')

        elif rebuild_tf_package:
            print('start rebuild TF and OTA package!')
            copy_apks_and_so()
            if use_bambu:
                copy_bambu()
            build_tf_and_ota()
        elif test_copy_inner:
            print('copy inner system!')
            copy_apk_to_system_app(get_inner_system_apks_dir())
        else:
            build_default_project()
