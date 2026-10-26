PRODUCT_VERSION_MAJOR = 17
PRODUCT_VERSION_MINOR = 0

# Bluenixx version
BLUENIXX_VERSION ?= 1.2
BLUENIXX_CODENAME ?= PHOENIX-A

ifeq ($(LINEAGE_VERSION_APPEND_TIME_OF_DAY),true)
    LINEAGE_BUILD_DATE := $(shell date -u +%Y%m%d_%H%M%S)
else
    LINEAGE_BUILD_DATE := $(shell date -u +%Y%m%d)
endif

# Set LINEAGE_BUILDTYPE from the env RELEASE_TYPE, for jenkins compat

ifndef LINEAGE_BUILDTYPE
    ifdef RELEASE_TYPE
        # Starting with "LINEAGE_" is optional
        RELEASE_TYPE := $(shell echo $(RELEASE_TYPE) | sed -e 's|^LINEAGE_||g')
        LINEAGE_BUILDTYPE := $(RELEASE_TYPE)
    endif
endif

# Bluenixx: OFFICIAL só com flag de mantenedor + product mantido por ele
ifeq ($(LINEAGE_BUILDTYPE),OFFICIAL)
    ifeq ($(filter $(BLUENIXX_MAINTAINER):$(TARGET_PRODUCT),$(shell cat vendor/bluenixx_maintainers/bluenixx.maintainers 2>/dev/null)),)
        $(info Bluenixx: OFFICIAL negado para '$(BLUENIXX_MAINTAINER):$(TARGET_PRODUCT)', build vira UNOFFICIAL)
        LINEAGE_BUILDTYPE := UNOFFICIAL
    endif
endif

# Filter out random types, so it'll reset to UNOFFICIAL
ifeq ($(filter OFFICIAL RELEASE NIGHTLY SNAPSHOT EXPERIMENTAL,$(LINEAGE_BUILDTYPE)),)
    LINEAGE_BUILDTYPE := UNOFFICIAL
    LINEAGE_EXTRAVERSION :=
endif

ifeq ($(LINEAGE_BUILDTYPE), UNOFFICIAL)
    ifneq ($(TARGET_UNOFFICIAL_BUILD_ID),)
        LINEAGE_EXTRAVERSION := -$(TARGET_UNOFFICIAL_BUILD_ID)
    endif
endif

# Bluenixx: sabor do build (GAPPS ou VANILLA)
ifeq ($(WITH_GMS),true)
    BLUENIXX_FLAVOR := GAPPS
else
    BLUENIXX_FLAVOR := VANILLA
endif

LINEAGE_VERSION_SUFFIX := $(LINEAGE_BUILD_DATE)-$(LINEAGE_BUILDTYPE)$(LINEAGE_EXTRAVERSION)-$(BLUENIXX_FLAVOR)-$(LINEAGE_BUILD)-v$(BLUENIXX_VERSION)-$(BLUENIXX_CODENAME)

# Internal version
LINEAGE_VERSION := $(PRODUCT_VERSION_MAJOR).$(PRODUCT_VERSION_MINOR)-$(LINEAGE_VERSION_SUFFIX)

# Display version
LINEAGE_DISPLAY_VERSION := $(PRODUCT_VERSION_MAJOR)-$(LINEAGE_VERSION_SUFFIX)

# LineageOS version properties
PRODUCT_PRODUCT_PROPERTIES += \
    ro.lineage.version=$(LINEAGE_VERSION) \
    ro.lineage.display.version=$(LINEAGE_DISPLAY_VERSION) \
    ro.lineage.build.version=$(PRODUCT_VERSION_MAJOR).$(PRODUCT_VERSION_MINOR) \
    ro.lineage.releasetype=$(LINEAGE_BUILDTYPE)

# Bluenixx flavor
PRODUCT_PRODUCT_PROPERTIES += ro.bluenixx.flavor=$(BLUENIXX_FLAVOR)

# Bluenixx version/codename
PRODUCT_PRODUCT_PROPERTIES += \
    ro.bluenixx.version=$(BLUENIXX_VERSION) \
    ro.bluenixx.codename=$(BLUENIXX_CODENAME)

PRODUCT_PRODUCT_PROPERTIES += \
    ro.bluenixx.build.date=$(LINEAGE_BUILD_DATE) \
    ro.bluenixx.buildtype=$(LINEAGE_BUILDTYPE)
