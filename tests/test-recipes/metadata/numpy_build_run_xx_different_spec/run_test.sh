echo $PATH
conda list -p $PREFIX --canonical
# Test the build string. Should contain NumPy, but not the version
conda list -p $PREFIX --canonical | grep "conda-build-test-numpy-build-run-xx-different-spec-1.0-np..py.._0"
