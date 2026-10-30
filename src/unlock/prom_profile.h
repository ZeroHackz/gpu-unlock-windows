#ifndef GU_PROM_PROFILE_H
#define GU_PROM_PROFILE_H
/* RUN03 hardware capture on the AD106 4060 Ti (10de:2805): BAR0+0x300000
 * reads the 1 MiB PROM; its first bytes are 55 AA (PCI ROM signature), so
 * the PROM begins at VBIOS offset 0. View [0,0xd6c00) hash is from the local
 * 1458:4123 card's RUN00 capture (prefix 55 AA confirmed there too). */
#define GU_PROM_BAR_OFFSET 0x300000U
#define GU_PROM_VIEW_BYTES 0xd6c00U
#define GU_PROM_VIEW_SHA256 "c99af86fe60fe849f4c730bd47d1c30622c411c4f00f151165f302d88d84533a"
#endif
