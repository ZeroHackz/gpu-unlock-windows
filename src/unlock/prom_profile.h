#ifndef GU_PROM_PROFILE_H
#define GU_PROM_PROFILE_H
/* RUN03 hardware capture on the AD106 4060 Ti (10de:2805): BAR0+0x300000
 * reads the 1 MiB PROM; its first bytes are 55 AA (PCI ROM signature), so
 * the PROM begins at VBIOS offset 0. View [0,0xd6c00) hash is from RUN03. */
#define GU_PROM_BAR_OFFSET 0x300000U
#define GU_PROM_VIEW_BYTES 0xd6c00U
#define GU_PROM_VIEW_SHA256 "53715948eb1a13aa9352e4602626abf4b6db9b8f9e09dea269d5d3b3f41394b0"
#endif
