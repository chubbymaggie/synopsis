
main (){

  const int * tab_of_ptr_to_const_int[12];
  
  float * const tab_of_const_ptr_to_float[10];
  
  int (* const tab_of_const_ptr_to_function_returning_an_int[5])(float, long);
  
  void (*function_returning_a_ptr_to_a_void_function (int, void(*)(int)))(int); 
  
  float (*(*(*ptr_to_an_array_of_ptr_to_function_returning_ptr_to_function_returning_a_float)[5])(char(*)(int)))(char);
  
}