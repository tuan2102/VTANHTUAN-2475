from QuanLySinhVien import QuanLySinhVien
    
qlsv = QuanLySinhVien()
while (1 == 1):
        print("\n CHUONG TRINH QUAN LY SINH VIEN")
        print("==========================MENU======================")
        print("== 1.them sinh vien ==")
        print("== 2cap nhap thong tin sinh vien boi ID ==")
        print("== 3xoa sinh vien boi ID ==")
        print("== 4tim kiem sinh vien theo ten ==")
        print("== 5sep xep sinh vien theo diem trung binh ==")
        print("== 6sep xep sinh vien theo diem chuyen nganh ==")
        print("== 7 hien thi danh sach sinh vien ==")
        print("== 0thoat ==")
        print("====================================================")
        
        key = int (input("nhap tuy chon:"))
        if(key == 1):
            print("\n1. them sinh vien.")
            qlsv.nhapSinhVien()
            print("\nthem sinh vien thanh cong!")
        elif (key == 2):
            if (qlsv.soLuongSinhVien() > 0):
                print("\n. cap nhap thanh tin sinh vien. ")
                print("\nNhap ID: ")               
                ID = int (input())
                qlsv.updateSinhVien (ID)
            else:
                    print("\nSanh sach sinh vien trong!")
        elif (key == 3 ):
            if (qlsv.soLuongSinhVien ()> 0 ) :
                print("\n3. Xoa sinh vien.")
                print("\nNhap ID: ")
                ID = int (input())
                if (qlsv.deleteById(ID)):
                    print("\nSinh vien co id = ", ID, " da bi xoa.")
                else:
                    print("\nSinh vien co id = ", ID," khong ton tai.")
            else:
                    print("\nSanh sach sinh vien trong!")
        elif (key == 4 ) :
                    if (qlsv.soLuongSinhVien ()> 0 ):
                        print("\n4. Tim kiem sinh vien theo ten.")
                        print("\nNhap ten de tim kiem: ")
                        name = input ()
                        searchResult = qlsv.findByName(name) 
                        qlsv.showSinhVien(searchResult)
                    else:
                        print("\nSanh sach sinh vien trong!")
        elif (key == 5):                
                if (qlsv.soLuongSinhVien() > 0):
                        print("\n5. Sap xep sinh vien theo diem trung bình (GPA).")
                        qlsv.sortByDiemTB ()
                        qlsv.showSinhVien(qlsv.getListSinhVien ())
                else:
                        print("\nSanh sach sinh vien trong!")
        elif (key == 6 ):
                    if (qlsv.soLuongSinhVien () > 0):
                        print("\n6. Sap xep sinh vien theo ten.")
                        qlsv.sortByName ()
                        qlsv.showSinhVien (qlsv.getListSinhVien())
                    else:
                        print("\nSanh sach sinh vien trong!")
        elif (key == 7 ) :
                    if (qlsv.soLuongSinhVien() > 0):
                        print("\n7. Hien thi danh sach sinh vien.")
                        qlsv.showSinhVien(qlsv.getListSinhVien())
                    else:
                        print("\nDanh sach sinh vien trong!")
        elif (key == 0 ) :
                print("\nBan da chon thoat chuong trinh!")
                break
        else:
                print("\nKhong co chuc nang nay!")
                print("\nHay chon chuc nang trong hop menu.")
                    
            
                
    