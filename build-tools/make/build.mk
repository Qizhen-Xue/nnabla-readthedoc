# Copyright 2018,2019,2020,2021 Sony Corporation.
# Copyright 2021 Sony Group Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

########################################################################################################################
# Suppress most of make message.
#.SILENT:

NNABLA_BUILD_INCLUDED = True

NNABLA_EXT_CUDA_DIRECTORY ?= $(shell cd ../nnabla-ext-cuda && pwd)
NNABLA_DIRECTORY ?= $(shell pwd)
include $(NNABLA_DIRECTORY)/build-tools/make/options.mk

########################################################################################################################
# Cleaning
.PHONY: nnabla-clean
nnabla-clean:
	@git clean -fdX

.PHONY: nnabla-clean-all
nnabla-clean-all:
	@git clean -fdx

# Touch the source file of .pyx to regenerate the cpp file.
.PHONY: touch-pyx-source-file
touch-pyx-source-file:
	touch $(NNABLA_DIRECTORY)/python/src/nnabla/*.pyx

########################################################################################################################
# Auto Format
.PHONY: nnabla-auto-format
nnabla-auto-format:
	cd $(NNABLA_DIRECTORY) && \
	python3 $(NNABLA_DIRECTORY)/build-tools/auto_format . --exclude \
		'\./src/nbla/(function|solver)/\w+\.cpp' \
		'\./src/nbla/init.cpp' \
		'\./python/src/nnabla/\w+\.(cpp|hpp|h|c)' \
		'\./python/src/nnabla/(solver.pyx|function.pyx|function.pxd|function_bases.py)' \
		'\./python/src/nnabla/utils/(save|load)_function.py' \
		'\./src/nbla_utils/nnp_impl_create_function.cpp' \
		'\./src/nbla_utils/nnabla\.pb\.(h|cc)' \
		'\./include/third_party/.*'

########################################################################################################################
# check copyright
.PHONY: nnabla-copyright-check
nnabla-check-copyright:
	python3 $(NNABLA_DIRECTORY)/build-tools/code_formatter/copyright_checker.py --rootdir=$(NNABLA_DIRECTORY)

########################################################################################################################
# Doc
.PHONY: nnabla-doc
nnabla-doc:
	mkdir -p $(DOC_DIRECTORY)
	cd $(DOC_DIRECTORY) \
	&& cmake -DBUILD_CPP_LIB=ON \
		-DBUILD_CPP_UTILS=OFF \
		-DBUILD_PYTHON_PACKAGE=ON \
		-DNNABLA_EXT_CUDA_DIRECTORY=$(NNABLA_EXT_CUDA_DIRECTORY) \
		$(CMAKE_OPTS) \
		$(NNABLA_DIRECTORY)
	make -C $(DOC_DIRECTORY) -j$(PARALLEL_BUILD_NUM) wheel doc


########################################################################################################################
# Third_party preparation for subsequent step of CI pipeline
.PHONY: nnabla-cpplib-collect
nnabla-cpplib-collect:
	@cd $(BUILD_DIRECTORY_CPPLIB) && \
	  if [ -d third_party/hdf5-master/bin ]; then \
	     find third_party/hdf5-master/bin -name "libhdf5*.*" \
	     -not -name "libhdf5*_tools.*" \
	     -not -name "libhdf5*_test.*" -print0\
	     |xargs -0 cp -Rt lib; \
	  fi


########################################################################################################################
# Build and test.
.PHONY: nnabla-cpplib
nnabla-cpplib:
	@mkdir -p $(BUILD_DIRECTORY_CPPLIB)
	@cd $(BUILD_DIRECTORY_CPPLIB) \
	&& cmake \
		-DBUILD_CPP_LIB=ON \
		-DBUILD_CPP_UTILS=ON \
		-DBUILD_PYTHON_PACKAGE=OFF \
		-DBUILD_TEST=ON \
		-DLIB_NAME_SUFFIX=$(LIB_NAME_SUFFIX) \
		-DNNABLA_UTILS_STATIC_LINK_DEPS=$(NNABLA_UTILS_STATIC_LINK_DEPS) \
		-DNNABLA_UTILS_WITH_HDF5=$(NNABLA_UTILS_WITH_HDF5) \
		-DNNABLA_UTILS_WITH_NPY=ON \
		-DPYTHON_VERSION_MAJOR=$(PYTHON_VERSION_MAJOR) \
		-DPYTHON_VERSION_MINOR=$(PYTHON_VERSION_MINOR) \
		$(CMAKE_OPTS) \
		$(NNABLA_DIRECTORY)
	@$(MAKE) -C $(BUILD_DIRECTORY_CPPLIB) -j$(PARALLEL_BUILD_NUM)
	@cd $(BUILD_DIRECTORY_CPPLIB) && cpack -G ZIP


.PHONY: nnabla-cpplib-android
nnabla-cpplib-android:
	@mkdir -p $(BUILD_DIRECTORY_CPPLIB_ANDROID)
	@cd $(BUILD_DIRECTORY_CPPLIB_ANDROID) \
	&& cmake \
	    -DCMAKE_TOOLCHAIN_FILE=$(NDK_PATH)/build/cmake/android.toolchain.cmake \
	    -DANDROID_ABI=$(EABI) \
	    -DANDROID_PLATFORM=$(PLATFORM) \
	    -DANDROID_STL=c++_shared \
	    -DCMAKE_SYSTEM_NAME=$(CMAKE_SYSTEM_NAME) \
	    -DBUILD_CPP_UTILS=ON \
	    -DBUILD_PYTHON_PACKAGE=OFF \
	    -DLIB_NAME_SUFFIX=$(LIB_NAME_SUFFIX) \
	    -DNNABLA_UTILS_WITH_HDF5=OFF \
	    -DPROTOC_COMMAND=$(SYSTEM_PROTOC) \
	    -DPYTHON_COMMAND_NAME=$(SYSTEM_PYTHON) \
            -DLIB_NAME_SUFFIX=$(LIB_NAME_SUFFIX) \
            -LA \
	    $(NNABLA_DIRECTORY)
	@$(NDK_PATH)/prebuilt/linux-x86_64/bin/make -C $(BUILD_DIRECTORY_CPPLIB_ANDROID) -j$(PARALLEL_BUILD_NUM)
	@rm -rf $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)
	@mkdir -p $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)/$(EABI)
	@cp $(TOOLCHAIN_INSTALL_DIR)/lib/libarchive.so $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)/$(EABI)
	@cp $(TOOLCHAIN_INSTALL_DIR)/lib/libprotobuf.so $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)/$(EABI)
	@cp $(BUILD_DIRECTORY_CPPLIB_ANDROID)/lib/libnnabla.so $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)/$(EABI)
	@cp $(BUILD_DIRECTORY_CPPLIB_ANDROID)/lib/libnnabla_utils.so $(BUILD_DIRECTORY_CPPLIB_ANDROID)/build_$(PLATFORM)_$(ARCHITECTURE)/$(EABI)


.PHONY: nnabla-cpplib-android-test
nnabla-cpplib-android-test:
# Execute the binary on emulator

.PHONY: nnabla-wheel
nnabla-wheel:
	@mkdir -p $(BUILD_DIRECTORY_WHEEL)
	@cd $(BUILD_DIRECTORY_WHEEL) \
	&& cmake \
                -DBUILD_CPP_LIB=OFF \
                -DBUILD_PYTHON_PACKAGE=ON \
                -DCPPLIB_BUILD_DIR=$(BUILD_DIRECTORY_CPPLIB) \
                -DCPPLIB_LIBRARY=$(BUILD_DIRECTORY_CPPLIB)/lib/libnnabla$(LIB_NAME_SUFFIX).so \
                -DLIB_NAME_SUFFIX=$(LIB_NAME_SUFFIX) \
                -DMAKE_MANYLINUX_WHEEL=$(MAKE_MANYLINUX_WHEEL) \
                -DPYTHON_VERSION_MAJOR=$(PYTHON_VERSION_MAJOR) \
                -DPYTHON_VERSION_MINOR=$(PYTHON_VERSION_MINOR) \
                -DWHEEL_SUFFIX=$(WHEEL_SUFFIX) \
		$(CMAKE_OPTS) \
		$(NNABLA_DIRECTORY)
	@$(MAKE) -C $(BUILD_DIRECTORY_WHEEL) wheel

.PHONY: nnabla-wheel-dependencies
nnabla-wheel-dependencies:
	rm -rf $(BUILD_DIRECTORY_WHEEL)/dependencies
	mkdir -p $(BUILD_DIRECTORY_WHEEL)/dependencies
	for p in $$(cat $(NNABLA_DIRECTORY)/python/requirements.txt) ;\
	do \
		whl=$$(find ~/.cache/pip/wheels/ -type f -iname $$p\*cp$(PYTHON_VERSION_MAJOR)$(PYTHON_VERSION_MINOR)\*.whl |xargs ls -rt|head -1);\
		if [ -f $$whl ];\
		then \
			cp -v $$whl $(BUILD_DIRECTORY_WHEEL)/dependencies/;\
		fi; \
	done

.PHONY: nnabla-install-cpplib
nnabla-install-cpplib:
	@$(MAKE) -C $(BUILD_DIRECTORY_CPPLIB) install

.PHONY: nnabla-install
nnabla-install:
	-pip uninstall -y nnabla
	whl='$(shell find $(BUILD_DIRECTORY_WHEEL)/dist/ -type f -name nnabla$(shell echo $(WHEEL_SUFFIX) | sed -e 's/-/_/g')-*.whl)'; \
	if [ ! -z $$whl ] && [ -f $$whl ];\
	then \
	    pip install ${PIP_INS_OPTS} ${PIP_INS_OPTS_EXTRA} $$whl; \
	fi;
	-pip install ${PIP_INS_OPTS} ${PIP_INS_OPTS_EXTRA} -r $(NNABLA_DIRECTORY)/python/test_requirements.txt

.PHONY: nnabla-converter-install
nnabla-converter-install:
	-pip uninstall -y nnabla-converter
	whl='$(shell find $(BUILD_DIRECTORY_WHEEL)/dist/ -type f -name nnabla_converter-*.whl)'; \
	if [ ! -z $$whl ] && [ -f $$whl ] && [ "$$(uname -m)" != "aarch64" ];\
	then \
	    pip install ${PIP_INS_OPTS} ${PIP_INS_OPTS_EXTRA} $$whl; \
	fi;

########################################################################################################################
# Shell (for rapid development)
.PHONY: nnabla-shell
nnabla-shell:
	PS1="nnabla-build: " bash --norc -i

########################################################################################################################
# test
.PHONY: nnabla-test-cpplib
nnabla-test-cpplib: nnabla-cpplib nnabla-cpplib-collect
	@$(MAKE) -C $(BUILD_DIRECTORY_CPPLIB) cpplibtest
	@$(MAKE) -C $(BUILD_DIRECTORY_CPPLIB) test_nbla_utils
	@bash -c "(cd $(BUILD_DIRECTORY_CPPLIB) && ctest -R cpplibtest --output-on-failure)"
	# Do not test test_nbla_utils here, since it depends on data preparation.

.PHONY: nnabla-test
nnabla-test:
	$(call with-venv, $(NNABLA_DIRECTORY), \
			$(BUILD_DIRECTORY_WHEEL)/env, \
			-f build-tools/make/build.mk, nnabla-test-local)

.PHONY: nnabla-test-local
nnabla-test-local: nnabla-install nnabla-converter-install
	@cd $(BUILD_DIRECTORY_WHEEL) \
	&& PATH=$(PYTEST_PATH_EXTRA):$(PATH) \
	LD_LIBRARY_PATH=$(PYTEST_LD_LIBRARY_PATH_EXTRA):$(LD_LIBRARY_PATH) \
	$(NNABLA_DIRECTORY)/build-tools/make/pytest.sh ${PYTEST_OPTS} $(NNABLA_DIRECTORY)/python/test
	@python -m pytest ${PYTEST_OPTS} $(NNABLA_DIRECTORY)/src/nbla_utils/test
	$(NNABLA_DIRECTORY)/build-tools/make/test_nbla_utils.sh
